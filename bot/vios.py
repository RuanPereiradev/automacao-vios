"""Funções comuns das telas do VIOS.

O bot nunca clica na tela: abre os links pelo endereço e lê/preenche por JavaScript,
porque depois do login o VIOS abre um popup de Recado que não deve ser tocado.
"""
import re
import unicodedata
from urllib.parse import parse_qs, urlparse

from selenium.webdriver.support.ui import WebDriverWait

# número CNJ do processo: 0000000-00.0000.0.00.0000
CNJ = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")


def normalizar(texto):
    """Maiúsculas, sem acento e com um espaço só (para comparar textos da tela)."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sem_acento.upper().split())


def digitos(texto):
    return re.sub(r"\D", "", texto or "")


def ids_numericos(url):
    """Valores numéricos (3+ dígitos) da query da URL, ex.: o id do processo. Os ids não são fixos:
    servem para conferir que duas telas (Visualizar e edição) são do mesmo processo."""
    return {v for vs in parse_qs(urlparse(url).query).values() for v in vs if re.fullmatch(r"\d{3,}", v)}


def esperar_ajax(driver, timeout):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState === 'complete' && (!window.jQuery || jQuery.active === 0)")
    )


def abrir(driver, url, timeout):
    driver.get(url)
    esperar_ajax(driver, timeout)


def texto_pagina(driver):
    return driver.execute_script("return document.body.innerText || ''")


def links(driver, locator):
    """Links dos elementos (o próprio <a> ou o primeiro <a> dentro dele): [{texto, href}], sem repetir.
    Item apagado fica de fora: o VIOS continua listando, com o ícone "Apagada" na linha."""
    vistos, saida = set(), []
    for el in driver.find_elements(*locator):
        item = driver.execute_script(
            """
            const e = arguments[0];
            const a = e.matches('a[href]') ? e : e.querySelector('a[href]');
            const linha = e.closest('tr');
            return {texto: (e.innerText || e.textContent || '').trim(), href: a ? a.href : '',
                    apagado: !!(linha && linha.querySelector("[title='Apagada']"))};
            """,
            el,
        )
        if item["apagado"]:
            continue
        if item["href"] and not item["href"].startswith("javascript") and item["href"] not in vistos:
            vistos.add(item["href"])
            saida.append(item)
    return saida
