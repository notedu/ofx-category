# OFX Category

Aplicação web para importar extratos bancários no formato **OFX**, visualizar os lançamentos, categorizá-los automaticamente por regras e exportar os dados em **CSV** ou **XLSX**.

## Recursos

- Importação de arquivos `.ofx`.
- Visualização do saldo, período, conta e lançamentos do extrato.
- Exibição de datas e valores formatados para pt-BR e reais (BRL).
- Categorização automática baseada em regras determinísticas, sem IA generativa.
- Edição manual da categoria de cada lançamento.
- Salvamento de uma categoria como regra para lançamentos futuros.
- Persistência das regras em um banco local SQLite.
- Exportação dos lançamentos exibidos para CSV ou XLSX. Os arquivos são gerados no navegador, sem precisar manter um modelo de planilha.

## Tecnologias

- **Frontend:** Vue 3, TypeScript, Vite e Tailwind CSS.
- **Backend:** Python, FastAPI e `ofxparse`.
- **Banco local:** SQLite.
- **Planilha XLSX:** ExcelJS.

## Estrutura do projeto

```text
.
├── backend/
│   ├── categorization.py   # Regras, classificação e inicialização do SQLite
│   └── main.py             # API FastAPI e importação do OFX
└── frontend/
    ├── src/
    │   ├── components/     # Header e Footer
    │   └── App.vue         # Interface, categorias e exportações
    ├── package.json
    └── vite.config.ts      # Proxy de /api para o backend local
```

## Requisitos

- Python 3.10 ou superior.
- Node.js e npm.

## Como executar localmente

Abra dois terminais na pasta do projeto.

### 1. Instalar e iniciar o backend

Na raiz do repositório:

```bash
python -m venv .venv
```

Ative o ambiente virtual:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instale as dependências e inicie a API:

```bash
python -m pip install fastapi uvicorn python-multipart ofxparse
uvicorn main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

A API ficará disponível em `http://localhost:8000`. A documentação interativa do FastAPI fica em `http://localhost:8000/docs`.

### 2. Instalar e iniciar o frontend

Em outro terminal, na pasta `frontend/`:

```bash
npm install
npm run dev
```

Abra o endereço indicado pelo Vite, normalmente `http://localhost:5173`. Durante o desenvolvimento, as chamadas de `/api` são encaminhadas para o backend na porta `8000`.

## Como usar

1. Selecione um arquivo `.ofx` e clique em **Importar extrato**.
2. Confira o resumo e os lançamentos apresentados.
3. Escolha uma categoria na lista de cada lançamento. A aplicação sugere categorias automaticamente quando encontra uma regra correspondente.
4. Para reaproveitar uma alteração manual, clique em **Salvar regra**. A regra será aplicada aos próximos extratos compatíveis.
5. Use **Exportar** para baixar um CSV ou **Planilha (.xlsx)** para baixar um arquivo de planilha.

## Como funciona a categorização

A classificação não usa IA generativa. O backend normaliza a descrição e o favorecido (por exemplo, ignora diferenças entre maiúsculas, acentos e pontuação) e compara o texto com padrões armazenados no SQLite.

As regras iniciais cobrem descrições comuns, como recebimentos, aluguel, energia, supermercado e transporte. Regras salvas pelo usuário têm prioridade sobre as regras padrão. Se nenhuma regra corresponder, o lançamento fica sem categoria para revisão manual.

O banco `backend/categorization.sqlite3` é criado e inicializado automaticamente quando a API inicia. O arquivo é local e está listado no `.gitignore`; faça uma cópia dele se quiser preservar as regras personalizadas ao mover ou reinstalar o projeto.

## Exportações

CSV e XLSX incluem data, descrição, favorecido, categoria, valor, conta e identificador da transação. A exportação usa as categorias que estão atualmente na tela, inclusive alterações que ainda não foram salvas como regra.

- **CSV:** separado por ponto e vírgula e codificado em UTF-8, com BOM para facilitar a abertura em programas de planilha.
- **XLSX:** inclui cabeçalho formatado, filtro, primeira linha congelada, datas e valores monetários formatados.

## API

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/api/health` | Verifica se a API está ativa. |
| `POST` | `/api/upload/` | Recebe um arquivo OFX e retorna os dados do extrato e as categorias sugeridas. |
| `POST` | `/api/rules/` | Salva ou atualiza uma regra de categoria para lançamentos futuros. |

## Build do frontend

Na pasta `frontend/`:

```bash
npm run build
```

Os arquivos de produção são gerados em `frontend/dist/`.
