import unittest
from unittest import mock

from nucleo import navegador


class TestNavegador(unittest.TestCase):
    def test_bloquear_registra_script(self):
        driver = mock.MagicMock()
        navegador.bloquear_envios(driver)
        cmd, args = driver.execute_cdp_cmd.call_args[0]
        self.assertEqual(cmd, "Page.addScriptToEvaluateOnNewDocument")
        js = args["source"]
        for trecho in ("__somenteLeitura", "XMLHttpRequest", "sendBeacon", "requestSubmit",
                       "data-orelha-pesquisa", "__orelhaPesquisaLiberada", "__orelhaBarrados"):
            self.assertIn(trecho, js)

    def test_listas_do_modo_pesquisa(self):
        driver = mock.MagicMock()
        navegador.bloquear_envios(driver, permitidos=["Eventos.php", " "], proibidos=["act=del"])
        js = driver.execute_cdp_cmd.call_args[0][1]["source"]
        self.assertNotIn("__ORELHA_LISTAS__", js)
        self.assertIn('{"permitidos": ["eventos.php"], "proibidos": ["act=del"]}', js)
        self.assertIn('{"permitidos": [], "proibidos": []}', navegador.script_bloqueio())

    def test_envios_bloqueados_e_nivel(self):
        driver = mock.MagicMock()
        driver.execute_script.return_value = True
        self.assertTrue(navegador.envios_bloqueados(driver))
        self.assertEqual(navegador.nivel_bloqueio(driver), "pesquisa")
        driver.execute_script.side_effect = lambda js: "__somenteLeitura" in js
        self.assertEqual(navegador.nivel_bloqueio(driver), "total")
        driver.execute_script.side_effect = None
        driver.execute_script.return_value = None
        self.assertFalse(navegador.envios_bloqueados(driver))
        self.assertIsNone(navegador.nivel_bloqueio(driver))

    def test_pesquisa_liberada_remove_no_fim(self):
        driver = mock.MagicMock()
        driver.execute_cdp_cmd.return_value = {"identifier": "7"}
        with self.assertRaises(RuntimeError):
            with navegador.pesquisa_liberada(driver):
                raise RuntimeError("falhou no meio")
        cmds = [c[0][0] for c in driver.execute_cdp_cmd.call_args_list]
        self.assertEqual(cmds, ["Page.addScriptToEvaluateOnNewDocument", "Page.removeScriptToEvaluateOnNewDocument"])
        self.assertEqual(driver.execute_cdp_cmd.call_args_list[1][0][1], {"identifier": "7"})
        self.assertIn("= false", driver.execute_script.call_args_list[-1][0][0])

    def test_tentativas_barradas(self):
        driver = mock.MagicMock()
        driver.execute_script.return_value = ["XHR POST /x"]
        self.assertEqual(navegador.tentativas_barradas(driver), ["XHR POST /x"])
        driver.execute_script.side_effect = RuntimeError
        self.assertEqual(navegador.tentativas_barradas(driver), [])


if __name__ == "__main__":
    unittest.main()
