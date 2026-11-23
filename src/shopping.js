const amount = new Intl.NumberFormat('ru-RU');

function costRange(low, high) {
  return high === null
    ? 'от ' + amount.format(low) + ' ₽'
    : amount.format(low) + '–' + amount.format(high) + ' ₽';
}

export function setupBudget() {
  const form = document.querySelector('#budget');
  const rate = Number(document.querySelector('#outer-leather').dataset.rate);
  const fixedMaterials = Array.from(document.querySelectorAll('#supply-items [data-cost]'))
    .reduce((sum, item) => sum + Number(item.dataset.cost), 0);
  const tools = Array.from(form.querySelectorAll('input[name="tool"]'));
  const chooseAll = form.querySelector('#choose-tools');

  function update() {
    const hide = form.querySelector('input[name="hide"]:checked');
    const min = Number(hide.dataset.min) * rate;
    const max = hide.dataset.max ? Number(hide.dataset.max) * rate : null;
    const toolsCost = tools.reduce((sum, item) => sum + (item.checked ? Number(item.value) : 0), 0);
    const fixed = fixedMaterials + toolsCost;
    form.querySelector('#budget-total').textContent =
      costRange(min + fixed, max === null ? null : max + fixed);
    form.querySelector('#hide-note').textContent = max === null
      ? 'Полушкуры начинаются от ' + hide.dataset.min + ' дм². Одна стоит ' + costRange(min, null)
        + '. Магазин рассчитает окончательную сумму по площади выбранной шкуры.'
      : 'Для отреза ' + hide.dataset.min + '–' + hide.dataset.max + ' дм² кожа обойдётся примерно в '
        + costRange(min, max) + '. Шоурум в Нижнем Новгороде режет по запросу. Размер и цену отреза уточните до оплаты.';
    form.querySelector('#tool-total').textContent = amount.format(toolsCost) + ' ₽';
    chooseAll.textContent = tools.every((tool) => tool.checked) ? 'Снять отметки' : 'Выбрать все пять';
  }

  form.addEventListener('change', update);
  chooseAll.addEventListener('click', () => {
    const checked = !tools.every((tool) => tool.checked);
    tools.forEach((tool) => { tool.checked = checked; });
    update();
  });
  update();
}
