import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

UF = "SC"
MIN_HORAS = 18
ANO = 2026

base = Path(__file__).resolve().parent
pasta = base / "dados_inmet"
saida = base / "saida"
saida.mkdir(exist_ok=True)


def extrair_zips():
    # extrai dos zips so os csv de sc
    destino = pasta / "extraidos"
    destino.mkdir(exist_ok=True)
    for z in pasta.rglob("*.zip"):
        with zipfile.ZipFile(z) as arq:
            for nome in arq.namelist():
                nome_arq = Path(nome).name
                if f"_{UF}_" in nome_arq and nome_arq.lower().endswith(".csv"):
                    caminho = destino / nome_arq
                    if not caminho.exists():
                        caminho.write_bytes(arq.read(nome))


def listar_arquivos():
    # lista os csv de sc sem repetir
    achados = {}
    for p in pasta.rglob("*"):
        if p.suffix.lower() == ".csv" and f"_{UF}_" in p.name:
            achados[p.name] = p
    return [achados[nome] for nome in sorted(achados)]


def renomear(col):
    # padroniza o nome das colunas
    c = col.upper()
    if c.startswith("DATA"):
        return "data"
    if c.startswith("HORA"):
        return "hora"
    if "PRECIPITA" in c:
        return "chuva"
    if "TEMPERATURA DO AR" in c:
        return "temp"
    if "UMIDADE RELATIVA DO AR" in c:
        return "umidade"
    if "VENTO, VELOCIDADE" in c:
        return "vento"
    return col


def pegar_estacao(caminho):
    # le o nome da estacao no cabecalho
    with open(caminho, encoding="latin-1") as f:
        for i in range(8):
            linha = f.readline()
            if linha.upper().startswith("ESTACAO"):
                return linha.split(";")[1].strip()
    return caminho.name


def ler_arquivo(caminho):
    # le um csv e arruma os tipos
    df = pd.read_csv(caminho, sep=";", skiprows=8, decimal=",", encoding="latin-1")
    df = df.rename(columns=renomear)
    df = df[["data", "hora", "chuva", "temp", "umidade", "vento"]].copy()

    for c in ["chuva", "temp", "umidade", "vento"]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "."), errors="coerce")
        df.loc[df[c] <= -9990, c] = np.nan

    data = df["data"].astype(str).str.strip().str.replace("/", "-")
    hora = df["hora"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(4).str[:4]
    dt = pd.to_datetime(data + " " + hora, format="%Y-%m-%d %H%M", errors="coerce")
    if dt.isna().all():
        dt = pd.to_datetime(data + " " + hora, format="%d-%m-%Y %H%M", errors="coerce")

    df["datetime"] = dt - pd.Timedelta(hours=3)
    df["estacao"] = pegar_estacao(caminho)
    df = df.dropna(subset=["datetime"])
    return df[["datetime", "estacao", "chuva", "temp", "umidade", "vento"]]


def limpar(df):
    # tira duplicados e valores impossiveis
    df = df.drop_duplicates(subset=["estacao", "datetime"])
    df.loc[~df["temp"].between(-10, 50), "temp"] = np.nan
    df.loc[~df["umidade"].between(0, 100), "umidade"] = np.nan
    df.loc[df["chuva"] < 0, "chuva"] = np.nan
    df.loc[df["vento"] < 0, "vento"] = np.nan
    return df


def agregar_diario(df):
    # junta as medicoes de hora em hora em um valor por dia
    df["data"] = df["datetime"].dt.floor("D")
    dia = df.groupby(["estacao", "data"]).agg(
        temp_media=("temp", "mean"),
        temp_max=("temp", "max"),
        temp_min=("temp", "min"),
        chuva_mm=("chuva", lambda s: s.sum(min_count=1)),
        umidade_media=("umidade", "mean"),
        vento_medio=("vento", "mean"),
        horas_validas=("temp", "count"),
    ).reset_index()

    dia = dia[dia["horas_validas"] >= MIN_HORAS].copy()
    dia["ano"] = dia["data"].dt.year
    dia["mes"] = dia["data"].dt.month
    dia = dia[dia["ano"] == ANO].copy()
    colunas = ["temp_media", "temp_max", "temp_min", "chuva_mm", "umidade_media", "vento_medio"]
    dia[colunas] = dia[colunas].round(2)
    return dia.reset_index(drop=True)


extrair_zips()
arquivos = listar_arquivos()
#for a in arquivos: print(a.name)
print(len(arquivos), "arquivos encontrados")

partes = []
for arq in arquivos:
    partes.append(ler_arquivo(arq))

bruto = pd.concat(partes, ignore_index=True)
bruto = bruto[bruto["datetime"].dt.year == ANO].copy()
print("estacoes lidas:", bruto["estacao"].nunique())
print("linhas horarias com duplicatas:", len(bruto))

bruto = limpar(bruto)
print(bruto.groupby("estacao")[["temp", "chuva"]].count().sort_values("temp").to_string())
print("linhas horarias sem duplicatas:", len(bruto))

dia = agregar_diario(bruto)

dia.to_csv(saida / "dataset_inmet_diario_SC.csv", index=False, encoding="utf-8-sig")

print("linhas do dataset:", len(dia))
print("estacoes no dataset:", dia["estacao"].nunique())
print("anos:", sorted(dia["ano"].unique().tolist()))
print("\ndias por estacao:")
print(dia.groupby("estacao").size().sort_values().to_string())
print("\ndataset salvo em", saida)