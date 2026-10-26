<template>
  <footer class="mt-auto border-t border-[#e6eeeb] bg-white">
    <div class="mx-auto grid w-[calc(100%-2rem)] max-w-290 grid-cols-2 gap-x-4 gap-y-7 py-7 sm:w-[calc(100%-4rem)] sm:grid-cols-[1.6fr_.8fr_.9fr] sm:gap-12 sm:py-9">
      <section class="col-span-2 sm:col-span-1">
        <a class="inline-flex items-center gap-2 no-underline" href="#top" aria-label="OFXCategory, início">
          <img class="h-8.5 w-8.5" src="../assets/logo.svg" alt="">
          <span class="font-manrope text-base font-extrabold tracking-[-0.4px]">OFXCategory</span>
        </a>
        <p class="mt-3 max-w-85 text-sm leading-relaxed text-[#879497]">
          Mais clareza para entender seus lançamentos. Importe seu extrato OFX e organize cada movimentação em um só lugar.
        </p>
      </section>

      <section>
        <h2 class="mb-3 mt-1 text-sm font-bold text-[#33434a]">Organize seu extrato</h2>
        <p class="mb-2 text-xs leading-relaxed text-[#829093]">Consulte datas, descrições e valores dos lançamentos importados.</p>
        <p class="mb-2 text-xs leading-relaxed text-[#829093]">Defina uma categoria para cada movimentação do extrato.</p>
      </section>

      <section>
        <h2 class="mb-3 mt-1 text-sm font-bold text-[#33434a]">Projeto</h2>
        <a class="mb-2 block text-xs text-[#829093] no-underline hover:text-[#168a78]" href="https://github.com/notedu" target="_blank" rel="noreferrer">Github ↗</a>
        <p class="mb-2 text-xs leading-relaxed text-[#829093]">Uma ferramenta simples para dar contexto aos seus dados financeiros.</p>
      </section>
    </div>
    <div class="mx-auto flex w-[calc(100%-2rem)] flex-col gap-1 border-t border-[#edf1ef] py-4 text-xs text-[#9ba6a7] sm:w-[calc(100%-4rem)] sm:flex-row sm:justify-between sm:gap-4">
      <span>© {{ new Date().getFullYear() }} OFXCategory</span>
      <span>Feito para organizar seus lançamentos com clareza.</span>
    </div>
  </footer>
</template>
