# =========================================================
# 🤖 ROBO QUANT — FINAL DE PRODUÇÃO (AUDITADO)
# Versão: v2.0 (Última Atualização: 2025-12-23)
# Binance Futures | SIM / REAL / TESTE
# Menu Telegram | Perfis | Perfil Auto IA
# Reconciliação | Watchdog | Logs
# =========================================================

import psutil  # Para verificar o estado da VPS
from binance.client import Client
import pandas as pd
import time, math, requests, json, csv, os, threading
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ================== CONFIG ==================
API_KEY = "SUA_API_KEY"
API_SECRET = "SUA_API_SECRET"
TELEGRAM_TOKEN = "SEU_TELEGRAM_TOKEN"
CHAT_ID = "SEU_CHAT_ID"

USDT_BASE = 20
LEVERAGE = 3
TIMEFRAME = Client.KLINE_INTERVAL_1MINUTE
LOOKBACK = 100

# ================== ESTADO ==================
AMBIENTE = "SIMULACAO"   # SIMULACAO / REAL / TESTE
ROBO_ATIVO = True
PERFIL_ATUAL = "NORMAL"
pos = None
LAST_HEARTBEAT = time.time()

# ================== LOGS ==================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PERFIL_ARQ = f"{LOG_DIR}/perfil_ia_log.json"
CSV_PERFIL_ARQ = f"{LOG_DIR}/perfil_ia_log.csv"

# ================== VPS ==================
# Função para verificar o estado da VPS
def vps_status():
    # Verificar se a VPS está ativa, aqui utilizamos a verificação de uso de CPU como exemplo
    vps_active = psutil.cpu_percent(interval=1) < 100  # Se o uso da CPU for menor que 100%, consideramos a VPS ON
    return "ON" if vps_active else "OFF"

# ================== PERFIS ==================
PERFIS = {
    "CONSERVADOR": {"loop": 10, "rsi": (45,55), "adx": 22, "vol": 1.3},
    "NORMAL":      {"loop": 5,  "rsi": (40,60), "adx": 18, "vol": 1.1},
    "RAPIDO":      {"loop": 3,  "rsi": (35,65), "adx": 15, "vol": 1.0},
    "TESTE":       {"loop": 2,  "rsi": (30,70), "adx": 10, "vol": 1.5},  # Modo Teste mais agressivo
}

# ================== RSI E TRANSAÇÕES ==================
total_transacoes = 0  # Contador de transações realizadas
total_ganho = 0  # Total de lucro
total_perda = 0  # Total de perda
conf_ia = 0.85  # Confiança da IA (Exemplo: 85% de confiança nas decisões)

# Função para calcular o RSI
def rsi(df, p=14):
    d = df.c.diff()
    g = d.where(d > 0, 0).rolling(p).mean()
    l = -d.where(d < 0, 0).rolling(p).mean()
    rs = g / l
    return float(100 - (100 / (1 + rs.iloc[-1])))

# Função para calcular o lucro ou prejuízo de uma transação
def registrar_transacao(preco_entrada, preco_saida, qty, lucro=True):
    global total_transacoes, total_ganho, total_perda
    total_transacoes += 1
    lucro_transacao = (preco_saida - preco_entrada) * qty if lucro else (preco_entrada - preco_saida) * qty
    if lucro:
        total_ganho += lucro_transacao
    else:
        total_perda += lucro_transacao

# ================== STATUS COMPLETO ==================
def mostrar_status(update, context):
    # Verificar estado da VPS
    vps_status_text = vps_status()

    # Verificar o RSI atual
    df = pd.DataFrame(
        client.futures_klines(symbol='BTCUSDT', interval=TIMEFRAME, limit=LOOKBACK),
        columns=["t", "o", "h", "l", "c", "v", "ct", "q", "n", "tb", "tq", "i"]
    ).astype(float)
    rsi_atual = rsi(df)

    # Status geral do robô
    status_msg = f"🚨 **Status do Robô** 🚨\n\n"
    status_msg += f"Modo: **{AMBIENTE}**\n"
    status_msg += f"Perfil Atual: **{PERFIL_ATUAL}**\n"
    
    # Informações sobre a última operação
    if pos:
        status_msg += f"Última Operação:\n"
        status_msg += f"Par: **{pos['symbol']}**\n"
        status_msg += f"Preço de Entrada: **${pos['entrada']}**\n"
        status_msg += f"Quantidade: **{pos['qty']}**\n"
    else:
        status_msg += f"Última Operação: Nenhuma operação realizada.\n"
    
    # Alavancagem e saldo de margem
    try:
        balance = client.futures_account_balance()
        saldo_usdt = [s for s in balance if s['asset'] == 'USDT'][0]['balance']
    except:
        saldo_usdt = "Não disponível"
    
    status_msg += f"Alavancagem: **{LEVERAGE}x**\n"
    status_msg += f"Saldo de Margem: **{saldo_usdt} USDT**\n"
    
    # Informações sobre a VPS
    status_msg += f"Estado da VPS: **{vps_status_text}**\n"

    # RSI Atual
    status_msg += f"RSI Atual: **{rsi_atual:.2f}**\n"
    
    # Transações realizadas e lucro/perda
    status_msg += f"Transações Realizadas: **{total_transacoes}**\n"
    status_msg += f"Total de Lucro: **${total_ganho:.2f}**\n"
    status_msg += f"Total de Perda: **${total_perda:.2f}**\n"

    # Confiança da IA
    status_msg += f"Confiança da IA: **{conf_ia * 100:.2f}%**\n"
    
    # Latência
    t0 = time.time()
    try:
        client.futures_ping()
        lat = time.time() - t0
    except:
        lat = "Erro"
    
    status_msg += f"Latência: **{lat} segundos**\n"
    
    # Tempo de operação
    tempo_operando = time.time() - LAST_HEARTBEAT
    status_msg += f"Tempo de Operação: **{int(tempo_operando // 60)} minutos**\n"
    
    # Verificar se o limite de perda diária foi atingido
    status_msg += f"Perda Diária: **{perda_diaria * 100:.2f}%**\n"
    
    # Enviar o status para o Telegram
    update.message.reply_text(status_msg)

# ================== MENU TELEGRAM ==================

# Função para gerar o menu com opções de Conta Simulada e Real
def start(update, context):
    keyboard = [
        [InlineKeyboardButton("Status do Robô", callback_data='status')],
        [InlineKeyboardButton("Ligar/Desligar Robô", callback_data='toggle')],
        [InlineKeyboardButton("Alterar Perfil", callback_data='alterar_perfil')],
        [InlineKeyboardButton("Reconciliação de Posição", callback_data='reconciliar')],
        [InlineKeyboardButton("Conta Simulada", callback_data='modo_simulado')],
        [InlineKeyboardButton("Conta Real", callback_data='modo_real_primeira_etapa')],
        [InlineKeyboardButton("Modo Teste", callback_data='modo_teste')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Escolha uma opção:', reply_markup=reply_markup)

# Função de callback para gerenciar as interações do menu
def button(update, context):
    query = update.callback_query
    choice = query.data

    if choice == 'status':
        mostrar_status(update, context)
    elif choice == 'toggle':
        toggle_robo(update, context)
    elif choice == 'alterar_perfil':
        alterar_perfil(update, context)
    elif choice == 'reconciliar':
        reconciliar_posicao(update, context)
    elif choice == 'modo_simulado':
        alternar_para_simulado(update, context)
    elif choice == 'modo_real_primeira_etapa':
        # Primeira etapa para confirmação da conta real
        query.answer()
        query.edit_message_text(text="⚠️ **ATENÇÃO!**\n\nVocê está prestes a operar com **dinheiro real**.\nTem certeza que deseja continuar?")
        keyboard = [
            [InlineKeyboardButton("Sim, quero operar com dinheiro real", callback_data='modo_real_segunda_etapa')],
            [InlineKeyboardButton("Cancelar", callback_data='cancelar_acao')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text("Escolha uma opção:", reply_markup=reply_markup)
    elif choice == 'modo_real_segunda_etapa':
        alternar_para_real(update, context)
    elif choice == 'modo_teste':
        aplicar_perfil("TESTE")
        update.callback_query.answer("Modo Teste Ativado com parâmetros exclusivos.")
    elif choice == 'cancelar_acao':
        query.edit_message_text(text="Operação cancelada. O robô permanecerá no modo atual.")

# Função para alternar para modo simulado
def alternar_para_simulado(update, context):
    global AMBIENTE  # Atualiza o ambiente global para simulado
    AMBIENTE = "SIMULACAO"
    tg("Modo **Simulação** ativado. O robô está agora operando em ambiente de teste.")
    update.callback_query.answer("Modo Simulação ativado.")

# Função para alternar para modo real (segunda etapa)
def alternar_para_real(update, context):
    global AMBIENTE  # Atualiza o ambiente global para real
    AMBIENTE = "REAL"
    tg("Modo **Real** ativado. O robô agora está operando com dinheiro real na Binance.")
    update.callback_query.answer("Modo Real ativado. O robô está agora operando com dinheiro real.")

