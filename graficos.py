from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ANO = 2026
MIN_DIAS = 200
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

base = Path(__file__).resolve().parent
saida = base / "saida"
(saida / "graficos").mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid")

df = pd.read_csv(saida / "dataset_inmet_diario_SC.csv", parse_dates=["data"])
dia = df[df["ano"] == ANO].copy()

#mantem so estacoes com dias suficientes (0 = mantem todas)
dias_por_estacao = dia.groupby("estacao")["data"].count()
estacoes_ok = dias_por_estacao[dias_por_estacao >= MIN_DIAS].index
dia = dia[dia["estacao"].isin(estacoes_ok)]

#salva a imagem e mostra na tela
def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(saida / "graficos" / nome, dpi=200)
    plt.show()

#temperatura media diaria com media movel
def grafico_linha():
    serie = dia.groupby("data")["temp_media"].mean()
    movel = serie.rolling(15, center=True, min_periods=7).mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(serie.index, serie, color="lightgray", label="Média diária SC")
    ax.plot(movel.index, movel, color="tab:red", linewidth=2, label="Média móvel (15 dias)")
    ax.set(title=f"Temperatura média diária em SC ({ANO})", xlabel="Data", ylabel="Temperatura (°C)")
    ax.legend()
    salvar(fig, "g1_linha_temperatura.png")

#chuva de cada dia em uma grade mes x dia
def grafico_calendario():
    chuva_dia = dia.groupby("data")["chuva_mm"].mean()
    tabela = pd.DataFrame({"mes": chuva_dia.index.month,
                           "dia": chuva_dia.index.day,
                           "chuva": chuva_dia.values})
    tabela = tabela.pivot(index="mes", columns="dia", values="chuva")
    tabela = tabela.reindex(columns=range(1, 32))
    nomes = [MESES[m - 1] for m in tabela.index]
    teto = chuva_dia.quantile(0.95) #mudar pra .max() pra mostrar os dias extremos

    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(tabela, cmap="Blues", vmin=0, vmax=teto, linewidths=0.5, linecolor="white",
                yticklabels=nomes, cbar_kws={"label": f"Chuva (mm) - escala até {teto:.0f} mm"}, ax=ax)
    ax.set_facecolor("lightgray")
    ax.set(title=f"Chuva diária em SC ({ANO}) - média entre as estações", xlabel="Dia do mês", ylabel="Mês")
    plt.yticks(rotation=0)
    salvar(fig, "g2_calendario_chuva.png")

#chuva acumulada por mes (media entre as estacoes)
def grafico_barras():
    chuva_dia = dia.groupby("data")["chuva_mm"].mean()
    chuva_mes = chuva_dia.groupby(chuva_dia.index.month).sum()
    nomes = [MESES[m - 1] for m in chuva_mes.index]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(nomes, chuva_mes.values, color="tab:blue")
    ax.set(title=f"Chuva mensal em SC ({ANO}) - média entre as estações", xlabel="Mês", ylabel="Chuva (mm)")
    salvar(fig, "g3_barras_chuva.png")

#numeros para usar nos slides
def mostrar_destaques():
    print("registros de", ANO, ":", len(dia))
    print("estacoes:", dia["estacao"].nunique())
    print("\ndia mais quente:")
    print(dia.loc[dia["temp_max"].idxmax(), ["data", "estacao", "temp_max"]].to_string())
    print("\ndia mais frio:")
    print(dia.loc[dia["temp_min"].idxmin(), ["data", "estacao", "temp_min"]].to_string())
    print("\nmaior chuva em um dia:")
    print(dia.loc[dia["chuva_mm"].idxmax(), ["data", "estacao", "chuva_mm"]].to_string())

    chuva_dia = dia.groupby("data")["chuva_mm"].mean()
    print("\nchuva por mes (mm):")
    print(chuva_dia.groupby(chuva_dia.index.month).sum().round(1).to_string())
    print("\ntemperatura media por mes (C):")
    print(dia.groupby("mes")["temp_media"].mean().round(1).to_string())


grafico_linha()
grafico_calendario()
grafico_barras()
mostrar_destaques()