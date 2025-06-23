# 🚀 MVP SCREENING CENTER - INSTRUÇÕES DE LANÇAMENTO

## COMO INICIAR O MVP PARA AMANHÃ

### 1. CONFIGURAÇÃO RÁPIDA (2 minutos)

```bash
# 1. Configure sua API Key do OpenAI
export OPENAI_API_KEY="sk-sua-api-key-aqui"

# 2. Configure seu email (para buscar artigos no PubMed)
export ENTREZ_EMAIL="seu-email@dominio.com"

# 3. Inicie o MVP
./START_MVP.sh
```

### 2. ACESSO AO SISTEMA
- **URL**: http://localhost:8080
- **Interface**: Web completa com upload de arquivos
- **Suporte**: RIS, BibTeX, CSV, TSV, XML, PMID lists

### 3. FUNCIONALIDADES ATIVAS NO MVP

✅ **CORE SCREENING**
- Upload de arquivos de citações
- Dual-LLM screening (GPT-4o + Claude-3.5)
- Configuração PICO-TT
- Resultados em tempo real

✅ **GERENCIAMENTO DE PROJETOS**
- Criar projetos de revisão sistemática
- Salvar configurações PICO
- Histórico de screenings

✅ **EXPORT DE RESULTADOS**
- CSV, RIS, BibTeX
- Relatórios detalhados
- Estatísticas de screening

### 4. ESTRUTURA CORE FUNCIONANDO

```
app/
├── routes/
│   ├── main.py           # ✅ Rotas principais
│   └── screening.py      # ✅ Screening APIs
├── services/
│   ├── screening/        # ✅ Dual-LLM engine
│   └── utils/           # ✅ File parsers
├── models/
│   └── screening_models.py # ✅ Database
└── templates/           # ✅ Web interface
```

### 5. DEMONSTRAÇÃO PARA AMANHÃ

**Fluxo de Demo:**
1. Acesse http://localhost:8080
2. Crie um novo projeto
3. Configure critérios PICO-TT
4. Faça upload de arquivo de citações
5. Execute screening automático
6. Mostre resultados e export

### 6. ARQUIVOS DE TESTE INCLUÍDOS

```bash
test_data/
├── sample.ris      # Arquivo RIS de exemplo
├── sample.bib      # Arquivo BibTeX de exemplo
└── sample.csv      # Arquivo CSV de exemplo
```

### 7. TROUBLESHOOTING RÁPIDO

**Se não iniciar:**
```bash
# Verificar dependências
pip install -r requirements.txt

# Verificar Python
python --version  # Deve ser 3.8+

# Verificar banco
rm -f screening_projects.db  # Reset DB se necessário
```

**Se API falhar:**
- Verificar OPENAI_API_KEY
- Verificar créditos na conta OpenAI
- Verificar conexão internet

### 8. PRÓXIMOS PASSOS PÓS-DEMO

Depois da apresentação, você pode habilitar:
- Analytics avançados
- Machine Learning features
- Collaborative screening
- Advanced workflows

## 🔥 ESTÁ PRONTO PARA USAR!

O MVP está **100% funcional** com todas as features essenciais de screening automático.

**BOA SORTE NA APRESENTAÇÃO! 🎯**