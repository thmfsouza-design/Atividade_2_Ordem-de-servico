import hmac
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from database import (
    STATUS_OS,
    DatabaseError,
    atualizar_ordem,
    criar_ordem,
    excluir_ordem,
    listar_ordens,
    validar_cliente,
    validar_ordem,
)


load_dotenv()
st.set_page_config(page_title="TechFix | Painel do gerente", page_icon="🔧", layout="wide")


def configurar_secrets():
    try:
        supabase_secrets = st.secrets.get("supabase", {})
        os.environ.setdefault("SUPABASE_URL", supabase_secrets.get("url", ""))
        os.environ.setdefault(
            "SUPABASE_SERVICE_ROLE_KEY", supabase_secrets.get("service_role_key", "")
        )
        return st.secrets.get("admin", {}).get("password", "") or os.getenv(
            "TECHFIX_ADMIN_PASSWORD", ""
        )
    except Exception:
        return os.getenv("TECHFIX_ADMIN_PASSWORD", "")


def mostrar_login(senha_configurada: str) -> None:
    st.title("TechFix Informática")
    st.subheader("Painel do gerente")
    if not senha_configurada:
        st.error("Configure a senha do gerente em [admin] no secrets.toml ou em TECHFIX_ADMIN_PASSWORD.")
        st.stop()
    with st.form("login_gerente"):
        senha = st.text_input("Senha do gerente", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")
    if entrar:
        if hmac.compare_digest(senha, senha_configurada):
            st.session_state.gerente_autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()


senha_gerente = configurar_secrets()
if not st.session_state.get("gerente_autenticado", False):
    mostrar_login(senha_gerente)

with st.sidebar:
    st.title("TechFix")
    st.caption("Painel de gerenciamento")
    busca = st.text_input("Buscar cliente, e-mail ou equipamento")
    filtro_status = st.multiselect("Status", STATUS_OS, default=STATUS_OS)
    st.divider()
    if st.button("Sair", width="stretch"):
        st.session_state.gerente_autenticado = False
        st.rerun()

st.title("Ordens de serviço")
try:
    ordens = listar_ordens()
except DatabaseError as exc:
    st.error(str(exc))
    st.stop()

df = pd.DataFrame(ordens)
if df.empty:
    df = pd.DataFrame(
        columns=[
            "id", "cliente_id", "nome", "email", "celular", "equipamento", "problema",
            "observacoes", "status", "criado_em", "atualizado_em",
        ]
    )
else:
    df["criado_em"] = pd.to_datetime(df["criado_em"], errors="coerce", utc=True)

filtrado = df[df["status"].isin(filtro_status)] if filtro_status else df.iloc[0:0]
if busca:
    colunas_busca = ["nome", "email", "equipamento"]
    mascara = pd.Series(False, index=filtrado.index)
    for coluna in colunas_busca:
        mascara |= filtrado[coluna].fillna("").astype(str).str.contains(busca, case=False, regex=False)
    filtrado = filtrado[mascara]

tab_consultar, tab_cadastrar, tab_editar, tab_indicadores = st.tabs(
    ["Consultar", "Cadastrar", "Editar/Excluir", "Indicadores"]
)

with tab_consultar:
    st.subheader("Ordens de serviço")
    st.dataframe(
        filtrado[["id", "nome", "email", "celular", "equipamento", "problema", "status", "criado_em"]],
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "Exportar CSV",
        data=filtrado.to_csv(index=False).encode("utf-8-sig"),
        file_name="techfix_ordens_servico.csv",
        mime="text/csv",
        width="content",
    )

with tab_cadastrar:
    st.subheader("Nova ordem de serviço")
    with st.form("nova_os", clear_on_submit=True):
        nome_novo = st.text_input("Nome do cliente")
        email_novo = st.text_input("E-mail do cliente")
        celular_novo = st.text_input("Celular com DDD")
        equipamento_novo = st.text_input("Equipamento")
        problema_novo = st.text_area("Problema relatado")
        observacoes_novas = st.text_area("Observações")
        salvar_nova = st.form_submit_button("Cadastrar OS", type="primary")
    if salvar_nova:
        try:
            cliente = validar_cliente(nome_novo, email_novo, celular_novo)
            ordem = validar_ordem(equipamento_novo, problema_novo, observacoes_novas)
            nova = criar_ordem(cliente, ordem)
            st.success(f"OS #{nova['id']} cadastrada com status Aberto.")
            st.rerun()
        except (ValueError, DatabaseError) as exc:
            st.error(str(exc))

with tab_editar:
    st.subheader("Editar ou excluir uma ordem")
    if df.empty:
        st.info("Ainda não há ordens cadastradas.")
    else:
        opcoes = {
            f"OS #{int(row.id)} · {row.nome} · {row.equipamento}": row
            for row in df.itertuples(index=False)
        }
        selecionada_label = st.selectbox("Selecione a OS", list(opcoes))
        selecionada = opcoes[selecionada_label]
        with st.form("editar_os"):
            nome_editado = st.text_input("Nome do cliente", value=selecionada.nome)
            email_editado = st.text_input("E-mail do cliente", value=selecionada.email)
            celular_editado = st.text_input("Celular", value=selecionada.celular)
            equipamento_editado = st.text_input("Equipamento", value=selecionada.equipamento)
            problema_editado = st.text_area("Problema", value=selecionada.problema)
            observacoes_editadas = st.text_area("Observações", value=selecionada.observacoes or "")
            status_editado = st.selectbox(
                "Status", STATUS_OS, index=STATUS_OS.index(selecionada.status)
            )
            salvar_edicao = st.form_submit_button("Salvar alterações", type="primary")
        if salvar_edicao:
            try:
                cliente_editado = validar_cliente(nome_editado, email_editado, celular_editado)
                ordem_editada = validar_ordem(
                    equipamento_editado, problema_editado, observacoes_editadas
                )
                ordem_editada["status"] = status_editado
                atualizar_ordem(
                    int(selecionada.id), selecionada.cliente_id, cliente_editado, ordem_editada
                )
                st.success(f"OS #{int(selecionada.id)} atualizada.")
                st.rerun()
            except (ValueError, DatabaseError) as exc:
                st.error(str(exc))
        confirmar_exclusao = st.checkbox(
            f"Confirmo a exclusão permanente da OS #{int(selecionada.id)}"
        )
        if st.button("Excluir OS", disabled=not confirmar_exclusao):
            try:
                excluir_ordem(int(selecionada.id))
                st.success("Ordem excluída.")
                st.rerun()
            except DatabaseError as exc:
                st.error(str(exc))

with tab_indicadores:
    st.subheader("Indicadores de atendimento")
    total = len(filtrado)
    concluidas = int(filtrado["status"].isin(["Concluído", "Entregue"]).sum())
    abertas = int(filtrado["status"].isin(["Aberto", "Em análise", "Aguardando peça"]).sum())
    metricas = st.columns(3)
    metricas[0].metric("OS no filtro", total)
    metricas[1].metric("Em andamento", abertas)
    metricas[2].metric("Concluídas/entregues", concluidas)
    contagem = filtrado["status"].value_counts().reindex(STATUS_OS, fill_value=0)
    st.bar_chart(contagem.rename("Ordens"))