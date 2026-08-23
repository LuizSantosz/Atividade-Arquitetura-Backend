"""Plugin de cálculo de frete por estado de destino."""

from dominio import Fatura, ResultadoEmissao


class FreteCorrespondenciaPlugin:
    """Frete calculado por estado — tabela fixa sem infraestrutura externa."""

    nome = "Frete-Padrão"

    TABELA = {
        "SP": 50.00,
        "RJ": 30.00,
        "MG": 10.00,
        "RS": 40.00,
        "BA": 65.00,
    }
    FRETE_PADRAO = 50.00
    ISENCAO_ACIMA_DE = 5_000.00   # frete grátis para faturas acima desse valor

    def processar(self, fatura: Fatura, resultado: ResultadoEmissao) -> ResultadoEmissao:
        if resultado.valor_bruto >= self.ISENCAO_ACIMA_DE:
            resultado.frete = 0.0
            return resultado

        resultado.frete = self.TABELA.get(fatura.cliente.estado, self.FRETE_PADRAO)
        return resultado
