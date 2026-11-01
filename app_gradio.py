import gradio as gr
from dotenv import load_dotenv

from database import DatabaseError, criar_ordem, validar_cliente, validar_ordem


load_dotenv()


def enviar_ordem(nome, email, celular, equipamento, problema, observacoes):
    try:
        cliente = validar_cliente(nome, email, celular)
        ordem = validar_ordem(equipamento, problema, observacoes)
        resultado = criar_ordem(cliente, ordem)
        return f"## OS #{resultado['id']} aberta com sucesso. Status: **Aberto**."
    except ValueError as exc:
        return f"## Dados inválidos\n{exc}"
    except DatabaseError as exc:
        return f"## Não foi possível registrar a OS\n{exc}"


with gr.Blocks(title="TechFix Informática | Abrir OS") as demo:
    gr.Markdown("# TechFix Informática\n## Abertura de ordem de serviço")
    gr.Markdown("Informe seus dados e descreva o equipamento para iniciar o atendimento.")
    nome = gr.Textbox(label="Nome completo", max_lines=1)
    email = gr.Textbox(label="E-mail", max_lines=1, placeholder="voce@exemplo.com")
    celular = gr.Textbox(label="Celular com DDD", max_lines=1, placeholder="(11) 99999-9999")
    equipamento = gr.Textbox(label="Equipamento", max_lines=1, placeholder="Notebook, desktop, impressora...")
    problema = gr.Textbox(label="Problema relatado", lines=4, max_lines=8)
    observacoes = gr.Textbox(label="Observações adicionais (opcional)", lines=3, max_lines=6)
    enviar = gr.Button("Abrir ordem de serviço", variant="primary")
    resultado = gr.Markdown()
    enviar.click(
        fn=enviar_ordem,
        inputs=[nome, email, celular, equipamento, problema, observacoes],
        outputs=resultado,
    )


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())