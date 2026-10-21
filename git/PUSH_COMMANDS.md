# Публикация кода и обновление Zenodo — без статьи

Запись на Zenodo привязана к репозиторию **`Dev-Nikita/terramechanics-based`**.
Это меняет порядок действий: новая версия на Zenodo создаётся **не загрузкой
архива вручную, а новым release на GitHub**. Zenodo сам заберёт содержимое
репозитория и опубликует его как следующую версию.

Отсюда главное следствие по безопасности: **всё, что лежит в репозитории,
автоматически попадает в публичный архив Zenodo.** Поэтому в репозитории не
должно быть ничего, кроме кода.

Текущее состояние записи:

| Версия | DOI | Что внутри |
|---|---|---|
| 0.1 | 10.5281/zenodo.21862565 | первый релиз |
| 0.2 | 10.5281/zenodo.21864835 | код **до** исправления скольжения (19,3 кБ) |
| concept | 10.5281/zenodo.21862564 | резолвится на последнюю версию — сейчас 0.2 |

В статье стоит concept DOI, и Data availability утверждает, что по нему лежит
код, воспроизводящий результаты. Пока версия 1.2.0 не опубликована, это неверно.

---

## 1. Почему репозиторий живёт в `code/`

Git инициализируется **внутри `code/`**, а не в корне проекта. Тогда
`article.tex`, `submission/`, `reviews/` и `archive/` физически находятся вне
рабочего дерева Git — `git add -A` их не видит, и в release, а значит и в
Zenodo, они попасть не могут.

Не делайте `git init` в корне проекта. Если он там когда-то появится —
удалите корневой `.git` и работайте по инструкции ниже.

## 2. Обновление репозитория

```bash
cd "$HOME/Science Article 2025-/Terramechanics-based evaluation of anair-cushion-assisted wheeled vehicle on deformableterrain/code"

# если репозиторий ещё не склонирован сюда:
git init
git branch -M main
git remote add origin https://github.com/Dev-Nikita/terramechanics-based.git
git fetch origin
git reset --soft origin/main        # подхватить историю, оставив текущие файлы

python3 terramechanics_model.py     # должно пройти девять проверок
git add -A
git status                          # только .py, .json, .txt, .cff, .md, LICENSE
git commit -m "Equilibrium slip solved from force balance; nine limit-case checks; results regenerated"
git push origin main
```

Если в репозитории остались старые файлы, которых больше нет в `code/`,
`git add -A` удалит их из индекса — это правильно, архив Zenodo должен
соответствовать текущей версии кода.

## 3. Контроль перед каждым push

```bash
git ls-files | grep -Ei '\.(tex|pdf|docx|bib|bbl)$' && echo "СТОП: в индексе документ" || echo "OK: только код"
git diff --stat origin/main..HEAD
```

Первая команда должна напечатать `OK: только код`. Если напечатала `СТОП` —
`git rm --cached <файл>` и закоммитить заново.

## 4. Новая версия на Zenodo

```bash
git tag -a 1.2.0 -m "Equilibrium slip, nine limit-case checks"
git push origin 1.2.0
```

Затем на GitHub: **Releases → Draft a new release → выбрать тег 1.2.0 →
Publish release**. Zenodo подхватит релиз за несколько минут и создаст версию
1.2.0 со своим version DOI.

Проверить после этого:

1. Открыть https://doi.org/10.5281/zenodo.21862564 — должна открыться версия
   1.2.0, а не 0.2.
2. Скачать архив и убедиться, что в нём есть `terramechanics_model.py`
   с функцией `equilibrium_slip` и что внутри нет ни одного `.tex`, `.pdf`
   или `.docx`.
3. Записать version DOI новой версии — его стоит указать в ответе редактору
   как точную ссылку на использованный код.

Запасной путь, если интеграция с GitHub не сработает: на Zenodo открыть запись
→ **New version** → удалить старый файл → загрузить `zenodo/zenodo_v1.2.0.zip`
→ version `1.2.0` → Publish.

## 5. Что коммитится, а что нет

| Файл | В Git и Zenodo | Причина |
|---|---|---|
| `terramechanics_model.py` | да | на него ссылается Data availability |
| `fig1_schematic.py`, `fig2a_geometry.py` | да | генерируют Fig. 2 |
| `results.json` | да | машиночитаемый дамп всех значений |
| `requirements.txt`, `LICENSE`, `CITATION.cff`, `README.md` | да | метаданные |
| `article.tex`, `build/article.pdf`, `article.docx` | **нет** | неопубликованная рукопись |
| `submission/` целиком | **нет** | переписка с редакцией |
| `refs.bib`, `supplementary.tex` | **нет** | часть рукописи |
| `reviews/` | **нет** | отзывы конфиденциальны по правилам Elsevier |
| `archive/` | **нет** | первая подача и шаблоны |

Код сам по себе текст статьи не раскрывает, и публикация кода политикой
Elsevier не ограничена — ограничена публикация самой рукописи и отзывов.
