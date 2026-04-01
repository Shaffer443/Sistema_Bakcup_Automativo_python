# Backup Ágil — Instruções de Uso

## O que é
Programa leve para Windows que faz backup automático ou manual de pastas/arquivos
específicos para HD externo ou outra pasta (ideal antes de formatar o PC).

---

## Como instalar

### Pré-requisito: Python
1. Acesse https://www.python.org/downloads/
2. Baixe a versão mais recente (Python 3.11 ou superior)
3. **IMPORTANTE**: Durante a instalação, marque ✅ "Add Python to PATH"

### Primeira execução
1. Coloque os dois arquivos na mesma pasta:
   - `backup_agil.py`
   - `Iniciar_Backup_Agil.bat`
2. Dê duplo clique em `Iniciar_Backup_Agil.bat`
   - Ele instala dependências automaticamente e abre o programa

---

## Como usar

### Backup manual
1. **Origens**: Clique em "+ Pasta" para cada pasta do Ágil que você quer fazer backup
2. **Destino**: Clique em "Escolher..." e selecione seu HD externo ou pasta de destino
3. Clique em **▶ FAZER BACKUP AGORA**

### Backup automático
1. Marque a opção "Ativar backup automático"
2. Escolha frequência (diário ou semanal) e horário
3. Deixe o programa aberto na bandeja — ele fará o backup no horário configurado

---

## Arquivos gerados

| Arquivo | Descrição |
|---|---|
| `backup_config.json` | Suas configurações (origens, destino, agendamento) |
| `backup_log.txt` | Histórico de todos os backups realizados |

### Estrutura do backup no destino
```
HD_Externo/
└── Backup_20250401_080000/   ← pasta com data e hora
    ├── PastaAgil/
    ├── Documentos/
    └── ...
```

### Versões antigas
O campo "Versões a manter" controla quantos backups são guardados.
Exemplo: valor 3 = mantém os 3 mais recentes, deleta os mais antigos.

---

## Dica: Criar atalho na área de trabalho
1. Clique com botão direito em `Iniciar_Backup_Agil.bat`
2. Enviar para → Área de trabalho (criar atalho)

---

## Requisitos
- Windows 10 ou superior
- Python 3.11+ instalado com "Add to PATH" marcado
- Biblioteca `schedule` (instalada automaticamente pelo .bat)
