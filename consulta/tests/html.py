"""Construtores de HTML fictício para os testes (nomes, CPFs e telefones inventados)."""
CAB_TAREFAS = ("", "CI", "Tipo de tarefa", "Descrição", "Comentários", "Datas", "Envolvidos", "Ações")
SUF = "(PREVIDENCIÁRIO)- SOBRAL 2026"


def tarefa(ci, tipo, datas, selo="", descricao="DESCRICAO-SECRETA", comentario="COMENTARIO-SECRETO"):
    badge = f'<span class="vj-badge">{selo}</span> ' if selo else ""
    return (f'<tr><td><i class="vj-icon"></i></td><td>{ci}</td><td>{badge}<span>{tipo}</span></td>'
            f'<td><div class="limite-texto">{descricao}</div></td><td>{comentario}</td><td>{datas}</td>'
            '<td>Responsáveis: PESSOA-DA-EQUIPE</td><td></td></tr>')


def previ(nome):
    return f"{nome} {SUF}"


def ficha(linhas, blocos="", info=None):
    cab = "".join(f"<th>{c}</th>" for c in CAB_TAREFAS)
    info = f"Mostrando 1 a {len(linhas)} de {len(linhas)} registros" if info is None else info
    return ('<html><body><div class="vj-bloco-info-text-area">'
            '<p><strong><span>Cidade / UF</span>: </strong> <span>Cidade Fictícia / CE</span></p>'
            f'{blocos}</div><h4>Tarefas</h4><div class="dataTables_wrapper"><table><thead><tr>{cab}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table><div class="dataTables_info">{info}</div></div></body></html>')


def linha_lista(n, ci, area="Previdenciário", extra=""):
    return (f'<tr id="processos-lista_linha_{n}" data-processos_id="{ci}">'
            f'<td data-id="processos-lista_linha_{n}_processos_id">{ci}</td>'
            f'<td data-id="processos-lista_linha_{n}_nro_proc_html">CNJ: 0000000-00.2099.8.06.0001</td>'
            f'<td data-id="processos-lista_linha_{n}_clientes_nome">NOME-DO-CLIENTE</td>'
            f'<td data-id="processos-lista_linha_{n}_pr_areas_nome">{area}</td>'
            f'<td data-id="processos-lista_linha_{n}_valor_acao">99.999,99</td>'
            f'<td data-id="processos-lista_linha_{n}_obs_proc">OBS-INTERNA {extra}</td></tr>')


def lista(cpf_fmt, linhas, eco=True):
    campo = f'<form><input name="pesq[cpfcnpj]" value="{cpf_fmt}"></form>' if eco else ""
    return (f'<html><body>{campo}<table class="geratabela"><thead><tr><th>CI</th><th>Número</th><th>Cliente</th>'
            f'<th>Área</th><th>Valor</th><th>Obs</th></tr></thead><tbody>{"".join(linhas)}</tbody></table></body></html>')


def pessoas(*ids):
    return "<html><body>" + "".join(f'<a href="?pag=sys/clientes/clientes-vis.php&clientes_id={i}">ver</a>'
                                    for i in ids) + "</body></html>"


def formulario(cpf_fmt, celular="", residencial="", comercial=""):
    return ('<html><body><form>'
            '<input name="form[nome]" value="NOME-DO-CLIENTE">'
            f'<input name="form[cpfcnpj]" value="{cpf_fmt}">'
            f'<input name="form[tel_celular]" value="{celular}">'
            f'<input name="form[tel_residencial]" value="{residencial}">'
            f'<input name="form[tel_comercial]" value="{comercial}">'
            '<input name="clientes_x_contatos[0][tel_celular]" value="(88) 90000-0999">'
            '<input name="clientes_x_contatos[0][nome]" value="CONTATO-EXTRA">'
            '</form></body></html>')
