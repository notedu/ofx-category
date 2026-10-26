<script setup lang="ts">
import { computed, ref } from 'vue'
import Header from './components/Header.vue'
import Footer from './components/Footer.vue'

interface ApiTransaction {
  date: string
  amount: number
  memo: string | null
  payee: string | null
  id: string
  category: string | null
  category_source: 'default' | 'user' | null
}

interface StatementResponse {
  account_id: string | null
  balance: number | null
  start_date: string | null
  end_date: string | null
  transactions: ApiTransaction[]
}

interface DisplayTransaction extends ApiTransaction {
  category: string
  categorySource: 'default' | 'user' | 'manual' | null
  ruleSaved: boolean
  ruleError: string
}

const categories = [
  'Alimentação',
  'Casa e moradia',
  'Compras',
  'Educação',
  'Escritório',
  'Lazer',
  'Pessoal',
  'Receitas',
  'Saúde',
  'Serviços',
  'Transporte',
  'Transferência',
  'Outros',
]

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const statement = ref<StatementResponse | null>(null)
const transactions = ref<DisplayTransaction[]>([])
const loading = ref(false)
const errorMessage = ref('')
const savingRuleId = ref<string | null>(null)
const exportingXlsx = ref(false)
const exportError = ref('')

const transactionCount = computed(() => transactions.value.length)
const formattedBalance = computed(() => formatCurrency(statement.value?.balance ?? 0))

function formatCurrency(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'

  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function parseSpreadsheetDate(value: string) {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? value : date
}

function exportFileName(extension: 'csv' | 'xlsx') {
  const sourceName = selectedFile.value?.name.replace(/\.ofx$/i, '') || 'extrato'
  const safeName = sourceName.replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/^-|-$/g, '') || 'extrato'
  return `${safeName}.${extension}`
}

function downloadFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function csvCell(value: string | number) {
  if (typeof value === 'number') {
    return value.toLocaleString('pt-BR', { useGrouping: false, minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  let safeValue = value
  if (/^\s*[=+\-@]/.test(safeValue)) safeValue = `'${safeValue}`
  return `"${safeValue.replace(/"/g, '""')}"`
}

function exportCsv() {
  const headers = ['Data', 'Descrição', 'Favorecido', 'Categoria', 'Valor', 'Conta', 'ID da transação']
  const rows = transactions.value.map((transaction) => [
    transaction.date.replace(' ', 'T'),
    transaction.memo || transaction.payee || '',
    transaction.payee || '',
    transaction.category || 'Sem categoria',
    transaction.amount,
    statement.value?.account_id || '',
    transaction.id || '',
  ])
  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(';')).join('\r\n')
  downloadFile(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }), exportFileName('csv'))
  exportError.value = ''
}

async function exportXlsx() {
  exportingXlsx.value = true
  exportError.value = ''

  try {
    const { default: ExcelJS } = await import('exceljs')
    const workbook = new ExcelJS.Workbook()
    workbook.creator = 'OFXCategory'
    workbook.created = new Date()

    const worksheet = workbook.addWorksheet('Lançamentos', {
      views: [{ state: 'frozen', ySplit: 1 }],
    })
    worksheet.columns = [
      { header: 'Data', key: 'date', width: 21, style: { numFmt: 'dd/mm/yyyy hh:mm' } },
      { header: 'Descrição', key: 'description', width: 40 },
      { header: 'Favorecido', key: 'payee', width: 30 },
      { header: 'Categoria', key: 'category', width: 22 },
      { header: 'Valor', key: 'amount', width: 18, style: { numFmt: '"R$" #,##0.00;[Red]-"R$" #,##0.00' } },
      { header: 'Conta', key: 'account', width: 20 },
      { header: 'ID da transação', key: 'id', width: 22 },
    ]

    worksheet.addRows(transactions.value.map((transaction) => ({
      date: parseSpreadsheetDate(transaction.date),
      description: transaction.memo || transaction.payee || '',
      payee: transaction.payee || '',
      category: transaction.category || 'Sem categoria',
      amount: transaction.amount,
      account: statement.value?.account_id || '',
      id: transaction.id || '',
    })))
    worksheet.autoFilter = { from: 'A1', to: `G${transactions.value.length + 1}` }
    worksheet.getRow(1).height = 25
    worksheet.getRow(1).font = { bold: true, color: { argb: 'FFFFFFFF' } }
    worksheet.getRow(1).fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF168A78' },
    }

    const fileBuffer = await workbook.xlsx.writeBuffer()
    const fileBytes = new Uint8Array(fileBuffer)
    downloadFile(
      new Blob([fileBytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }),
      exportFileName('xlsx'),
    )
  } catch (error) {
    exportError.value = error instanceof Error ? error.message : 'Não foi possível gerar a planilha.'
  } finally {
    exportingXlsx.value = false
  }
}

function chooseFile() {
  fileInput.value?.click()
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  errorMessage.value = ''
}

function markCategoryManual(transaction: DisplayTransaction) {
  transaction.categorySource = transaction.category ? 'manual' : null
  transaction.ruleSaved = false
  transaction.ruleError = ''
}

function classificationLabel(transaction: DisplayTransaction) {
  if (transaction.ruleSaved) return 'Regra salva'
  if (transaction.categorySource === 'manual') return 'Alteração pendente'
  if (transaction.categorySource === 'user') return 'Sua regra'
  if (transaction.categorySource === 'default') return 'Automática'
  return 'Revisar'
}

async function saveRule(transaction: DisplayTransaction) {
  savingRuleId.value = transaction.id
  transaction.ruleError = ''

  try {
    const response = await fetch('/api/rules/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        memo: transaction.memo,
        payee: transaction.payee,
        category: transaction.category || null,
      }),
    })
    const result = await response.json()
    if (!response.ok) throw new Error(result.detail ?? 'Não foi possível salvar a regra.')

    transaction.categorySource = transaction.category ? 'user' : null
    transaction.ruleSaved = true
  } catch (error) {
    transaction.ruleError = error instanceof Error ? error.message : 'Falha ao salvar a regra.'
  } finally {
    savingRuleId.value = null
  }
}

async function enviar() {
  if (!selectedFile.value) {
    errorMessage.value = 'Selecione um arquivo OFX para continuar.'
    return
  }

  loading.value = true
  errorMessage.value = ''

  const data = new FormData()
  data.append('file', selectedFile.value)

  try {
    const response = await fetch('/api/upload/', { method: 'POST', body: data })
    const result = await response.json()

    if (!response.ok) {
      throw new Error(result.detail ?? `Não foi possível processar o arquivo (${response.status}).`)
    }

    statement.value = result as StatementResponse
    transactions.value = (statement.value.transactions ?? []).map((transaction) => ({
      ...transaction,
      category: transaction.category ?? '',
      categorySource: transaction.category_source,
      ruleSaved: false,
      ruleError: '',
    }))
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Ocorreu um erro ao enviar o arquivo. Tente novamente.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div id="top" class="flex min-h-screen flex-col">
    <Header />

    <main class="mx-auto w-[calc(100%-28px)] max-w-290 flex-1 py-8 sm:w-[calc(100%-64px)] sm:py-14">
      <section class="mb-6 flex min-h-28 items-center justify-between sm:mb-8 sm:min-h-30" aria-labelledby="page-title">
        <div>
          <p class="mb-2 text-xs font-bold tracking-[1.45px] text-[#168a78]">VISÃO GERAL</p>
          <h1 id="page-title" class="max-w-165 font-manrope text-3xl font-bold leading-tight tracking-[-1px] text-[#1b2b32] sm:text-4xl">Seus extratos, mais organizados.</h1>
          <p class="mt-2 max-w-82.5 text-sm leading-relaxed text-[#77858b] sm:max-w-none sm:text-base">Importe seu arquivo OFX e organize cada lançamento do seu jeito.</p>
        </div>
        <div class="relative mr-5 hidden h-29 w-45 items-center justify-center sm:flex" aria-hidden="true">
          <span class="absolute h-28 w-28 rounded-full border border-[#d4ebe5]"></span>
          <span class="absolute h-19 w-19 rounded-full border border-[#d4ebe5]"></span>
          <span class="absolute left-21.75 top-2 h-3 w-3 rounded-full border-3 border-white bg-[#24a48e] shadow"></span>
          <span class="absolute left-7.25 top-15.75 h-3 w-3 rounded-full border-3 border-white bg-[#8cc9b9] shadow"></span>
          <span class="absolute left-34.75 top-18.25 h-3 w-3 rounded-full border-3 border-white bg-[#b4ded2] shadow"></span>
          <span class="absolute h-3.5 w-3.5 rotate-45 rounded-[5px] border-3 border-[#168a78] bg-white"></span>
        </div>
      </section>

      <section class="rounded-2xl border border-[#e6eeeb] bg-white p-5 shadow-sm sm:p-7" aria-labelledby="upload-title">
        <div class="flex items-start gap-3.5">
          <div class="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-[#e8f6f2] text-[#168a78]" aria-hidden="true">
            <svg class="h-5.25 w-5.25" viewBox="0 0 24 24" fill="none"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14.5v3A2.5 2.5 0 0 0 7.5 20h9a2.5 2.5 0 0 0 2.5-2.5v-3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" /></svg>
          </div>
          <div>
            <h2 id="upload-title" class="font-manrope text-lg font-bold">Importar extrato</h2>
            <p class="mt-1 max-w-85 text-sm leading-relaxed text-[#77858b]">Escolha um arquivo OFX para visualizar e categorizar seus lançamentos.</p>
          </div>
        </div>

        <form class="mt-5 flex flex-wrap items-center gap-2.5 rounded-xl border border-dashed border-[#cbdad5] bg-[#fbfdfc] p-2.5" @submit.prevent="enviar">
          <input ref="fileInput" class="sr-only" type="file" accept=".ofx,application/x-ofx" @change="onFileChange">
          <button class="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg border border-[#dce7e3] bg-white px-4 text-sm font-bold text-[#3c5550] transition hover:border-[#9bcabd] hover:bg-[#f5fbf9]" type="button" @click="chooseFile">
            <svg class="h-4 w-4 text-[#168a78]" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14.5v3A2.5 2.5 0 0 0 7.5 20h9a2.5 2.5 0 0 0 2.5-2.5v-3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" /></svg>
            {{ selectedFile ? 'Trocar arquivo' : 'Escolher arquivo' }}
          </button>
          <span class="min-w-0 flex-1 truncate text-sm text-[#8b989c]" :title="selectedFile?.name">{{ selectedFile?.name ?? 'Nenhum arquivo selecionado' }}</span>
          <button class="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-lg border border-[#168a78] bg-[#168a78] px-5 text-sm font-bold text-white transition hover:-translate-y-px hover:border-[#117362] hover:bg-[#117362] disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none" type="submit" :disabled="loading || !selectedFile">
            <span v-if="loading" class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/50 border-t-white" aria-hidden="true"></span>
            {{ loading ? 'Importando…' : 'Importar extrato' }}
          </button>
          <span class="order-last w-full px-1 text-xs text-[#98a3a5]">Formato aceito: .OFX</span>
        </form>
        <p v-if="errorMessage" class="mt-3 rounded-lg bg-[#fff2f1] px-3 py-2.5 text-xs text-[#9a3838]" role="alert">{{ errorMessage }}</p>
      </section>

      <template v-if="statement">
        <section class="my-5 grid grid-cols-2 gap-3 sm:my-6 sm:grid-cols-[1fr_1fr_1.45fr] sm:gap-5" aria-label="Resumo do extrato">
          <article class="flex min-h-24 items-center gap-3 rounded-[14px] border border-[#e8efed] bg-white p-4 shadow-sm sm:min-h-28 sm:gap-4 sm:p-5">
            <div class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#e7f5f0] text-sm font-bold text-[#17816f] sm:h-11 sm:w-11">R$</div>
            <div><p class="mb-1.5 text-xs text-[#77858b] sm:text-sm">Saldo do extrato</p><p class="font-manrope text-lg font-bold tracking-tight sm:text-2xl">{{ formattedBalance }}</p></div>
          </article>
          <article class="flex min-h-24 items-center gap-3 rounded-[14px] border border-[#e8efed] bg-white p-4 shadow-sm sm:min-h-28 sm:gap-4 sm:p-5">
            <div class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#f0effb] text-[#6358ad] sm:h-11 sm:w-11">
              <svg class="h-5.25 w-5.25" viewBox="0 0 24 24" fill="none"><path d="M7 4.75h10A2.25 2.25 0 0 1 19.25 7v10A2.25 2.25 0 0 1 17 19.25H7A2.25 2.25 0 0 1 4.75 17V7A2.25 2.25 0 0 1 7 4.75ZM8 9h8M8 12.5h8M8 16h4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
            </div>
            <div><p class="mb-1.5 text-xs text-[#77858b] sm:text-sm">Lançamentos</p><p class="font-manrope text-lg font-bold tracking-tight sm:text-2xl">{{ transactionCount }}</p></div>
          </article>
          <article class="col-span-2 flex min-h-24 items-center gap-3 rounded-[14px] border border-[#e8efed] bg-white p-4 shadow-sm sm:col-span-1 sm:min-h-28 sm:gap-4 sm:p-5">
            <div class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#fbf3e4] text-[#bf8b36] sm:h-11 sm:w-11">
              <svg class="h-5.25 w-5.25" viewBox="0 0 24 24" fill="none"><path d="M7.25 3.75v2.5m9.5-2.5v2.5M4.75 9h14.5M6.5 5.75h11A1.75 1.75 0 0 1 19.25 7.5v10A1.75 1.75 0 0 1 17.5 19.25h-11A1.75 1.75 0 0 1 4.75 17.5v-10A1.75 1.75 0 0 1 6.5 5.75Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
            </div>
            <div><p class="mb-1.5 text-xs text-[#77858b] sm:text-sm">Período do extrato</p><p class="font-manrope text-xs font-bold sm:text-sm">{{ formatDate(statement.start_date) }} <span class="px-1 text-[#a5b1b0]">—</span> {{ formatDate(statement.end_date) }}</p></div>
          </article>
        </section>

        <section class="overflow-hidden rounded-2xl border border-[#e6eeeb] bg-white shadow-sm" aria-labelledby="transactions-title">
          <div class="flex flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
            <div>
              <p class="mb-1 text-[10px] font-bold tracking-[1.2px] text-[#168a78]">EXTRATO IMPORTADO</p>
              <h2 id="transactions-title" class="font-manrope text-xl font-bold tracking-tight">Lançamentos</h2>
              <p class="mt-1 text-xs text-[#89969a]">Conta {{ statement.account_id || 'não identificada' }} <span class="px-1 text-[#bdc6c5]">·</span> {{ transactionCount }} {{ transactionCount === 1 ? 'lançamento' : 'lançamentos' }}</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button class="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[#dce7e3] bg-white px-3.5 text-xs font-semibold text-[#3c5550] transition hover:border-[#9bcabd] hover:bg-[#f5fbf9] disabled:cursor-not-allowed disabled:opacity-50" type="button" :disabled="!transactions.length" @click="exportCsv">
                <span class="rounded bg-[#e8f6f2] px-1.5 py-0.5 text-[10px] font-bold text-[#168a78]">CSV</span>
                Exportar
              </button>
              <button class="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[#168a78] bg-[#168a78] px-3.5 text-xs font-semibold text-white transition hover:border-[#117362] hover:bg-[#117362] disabled:cursor-not-allowed disabled:opacity-50" type="button" :disabled="!transactions.length || exportingXlsx" @click="exportXlsx">
                <span v-if="exportingXlsx" class="h-3 w-3 animate-spin rounded-full border-2 border-white/50 border-t-white" aria-hidden="true"></span>
                {{ exportingXlsx ? 'Gerando…' : 'Planilha (.xlsx)' }}
              </button>
              <span v-if="selectedFile" class="inline-flex max-w-full items-center gap-1.5 truncate rounded-lg border border-[#e6efec] bg-[#fbfdfc] px-2.5 py-2 text-[10px] text-[#697a7b] sm:max-w-65">
                <svg class="h-3.75 w-3.75 shrink-0 text-[#168a78]" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7.5 3.75h6l4.75 4.75v11A.75.75 0 0 1 17.5 20.25h-11a.75.75 0 0 1-.75-.75v-15a.75.75 0 0 1 .75-.75ZM13.25 4v4.75H18" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" /></svg>
                {{ selectedFile.name }}
              </span>
            </div>
          </div>
          <p v-if="exportError" class="mx-5 mb-4 rounded-lg bg-[#fff2f1] px-3 py-2.5 text-xs text-[#9a3838] sm:mx-7" role="alert">{{ exportError }}</p>

          <div v-if="transactions.length" class="overflow-x-auto">
            <table class="w-full min-w-190 border-collapse text-left">
              <thead class="bg-[#f8faf9]">
                <tr class="border-y border-[#edf1ef] text-[9px] font-bold tracking-[.65px] text-[#859195]">
                  <th class="w-35.5 whitespace-nowrap py-3 pl-6 pr-4">DATA</th>
                  <th class="min-w-58.75 px-4 py-3">DESCRIÇÃO</th>
                  <th class="min-w-43.75 px-4 py-3">CATEGORIA</th>
                  <th class="min-w-28.75 py-3 pl-4 pr-6 text-right">VALOR</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="transaction in transactions" :key="transaction.id" class="border-b border-[#eff2f1] last:border-0 hover:bg-[#fbfdfc]">
                  <td class="whitespace-nowrap py-4 pl-6 pr-4 text-xs text-[#65747a]">{{ formatDate(transaction.date) }}</td>
                  <td class="px-4 py-4">
                    <div class="flex min-w-51.25 items-center gap-2.5">
                      <span class="grid h-7.75 w-7.75 shrink-0 place-items-center rounded-[10px] bg-[#e8f5f1] text-xs font-bold text-[#247c6d]" :class="{ '!bg-[#f8f1df] !text-[#87713a]': transaction.amount > 0 }" aria-hidden="true">{{ (transaction.payee || transaction.memo || 'L').trim().charAt(0).toUpperCase() }}</span>
                      <span class="flex min-w-0 flex-col gap-0.75">
                        <strong class="max-w-57.5 truncate text-xs font-semibold text-[#33434a]">{{ transaction.payee || transaction.memo || 'Lançamento sem descrição' }}</strong>
                        <small class="text-[10px] text-[#9aa5a7]">{{ transaction.payee && transaction.memo ? transaction.memo : `Identificação ${transaction.id || '—'}` }}</small>
                        <span class="flex flex-wrap items-center gap-x-2 gap-y-1">
                          <small class="rounded-full px-1.5 py-0.5 text-[10px]" :class="classificationLabel(transaction) === 'Revisar' ? 'bg-[#fff5e7] text-[#9a6a24]' : classificationLabel(transaction) === 'Alteração pendente' ? 'bg-[#f1effb] text-[#6658a8]' : 'bg-[#e8f6f2] text-[#16806f]'">{{ classificationLabel(transaction) }}</small>
                          <button v-if="transaction.categorySource === 'manual'" class="text-[10px] font-semibold text-[#168a78] underline decoration-[#168a78]/40 underline-offset-2 hover:text-[#117362] disabled:opacity-50" type="button" :disabled="savingRuleId === transaction.id" @click="saveRule(transaction)">
                            {{ savingRuleId === transaction.id ? 'Salvando…' : 'Salvar regra' }}
                          </button>
                        </span>
                        <small v-if="transaction.ruleError" class="text-[9px] text-[#9a3838]">{{ transaction.ruleError }}</small>
                      </span>
                    </div>
                  </td>
                  <td class="px-4 py-4">
                    <select v-model="transaction.category" class="h-9 w-full min-w-34 rounded-[7px] border border-[#e6ece9] bg-white px-2.5 text-xs text-[#718084] outline-none focus:border-[#80bcad] focus:ring-2 focus:ring-[#168a78]/10" aria-label="Categoria do lançamento" @change="markCategoryManual(transaction)">
                      <option value="">{{ transaction.categorySource ? 'Sem categoria' : 'Revisar categoria' }}</option>
                      <option v-for="category in categories" :key="category" :value="category">{{ category }}</option>
                    </select>
                  </td>
                  <td class="whitespace-nowrap py-4 pl-4 pr-6 text-right text-xs font-bold tabular-nums" :class="transaction.amount >= 0 ? 'text-[#18816c]' : 'text-[#3a4950]'">
                    {{ formatCurrency(transaction.amount) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="grid place-items-center gap-2.5 px-5 py-10 text-xs text-[#829094]">
            <span class="grid h-8 w-8 place-items-center rounded-full bg-[#e8f6f2] text-[#168a78]">✓</span>
            <p class="m-0">O arquivo foi importado, mas não há lançamentos para exibir.</p>
          </div>
          <div class="flex flex-col gap-2 border-t border-[#edf1ef] px-5 py-4 text-xs text-[#96a1a3] sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-7">
            <span><span class="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-[#56ae99] align-[1px]"></span>A categoria pode ser ajustada em cada lançamento.</span>
            <span>Valores em reais (BRL)</span>
          </div>
        </section>
      </template>

      <section v-else class="mt-5 flex min-h-47.5 flex-col items-center justify-center gap-4 rounded-2xl border border-[#e8efed] bg-gradient-to-br from-white via-white to-[#f7fbf9] p-6 text-center sm:min-h-55 sm:flex-row sm:gap-7 sm:text-left" aria-label="Prévia do extrato">
        <div class="relative grid h-22 w-22.5 shrink-0 place-items-center rounded-3xl bg-[#f0f8f5] sm:h-33.75 sm:w-29" aria-hidden="true">
          <div class="flex h-18.25 w-14.25 -rotate-5 flex-col justify-center gap-1.75 rounded-[9px] border border-[#d7e8e2] bg-white px-2.5 py-3 shadow-lg shadow-[#1d5a47]/10">
            <span class="h-1 w-2/3 rounded-full bg-[#b6ddd2]"></span><span class="h-1 rounded-full bg-[#e6f0ed]"></span><span class="h-1 rounded-full bg-[#e6f0ed]"></span><span class="h-1 rounded-full bg-[#e6f0ed]"></span>
          </div>
          <span class="absolute right-6 top-5 text-sm text-[#4aa590]">✦</span><span class="absolute bottom-5 left-5 text-[11px] text-[#b1d9ce]">✦</span>
        </div>
        <div>
          <h2 class="font-manrope text-[17px] font-bold tracking-tight">Seu extrato aparecerá aqui</h2>
          <p class="mt-2 max-w-98.75 text-sm leading-relaxed text-[#879497]">Importe um arquivo OFX para ver datas, descrições e valores, e começar a categorizar suas movimentações.</p>
        </div>
      </section>
    </main>

    <Footer />
  </div>
</template>
