# JTERRA-D-26-00107 — проект статьи

Terramechanics-based evaluation of an air-cushion-assisted wheeled vehicle on
deformable terrain: feasibility limits and the energy-optimal load-relief fraction

Статус: ревизия после первого раунда рецензирования. Научная часть готова,
остаются два технических блокера — см. `submission/TODO_BEFORE_SUBMIT.md`.

## Структура

```
<корень проекта>/
├── article.tex            ГЛАВНЫЙ ФАЙЛ СТАТЬИ — править здесь
├── supplementary.tex      таблицы S1–S5
├── refs.bib               библиография, 32 источника, все проверены
├── elsarticle.cls         класс журнала
├── elsarticle-harv.bst    стиль библиографии
├── make_docx.py           сборка DOCX из .tex
│
├── figures/               все рисунки: рабочие имена и имена для журнала
├── build/                 article.pdf, article.docx, supplementary.*
│
├── submission/            загружается в Editorial Manager — НЕ публикуется
│   ├── cover_letter_revision.{md,docx}   письмо на ревизию (использовать это)
│   ├── cover_letter.{md,docx}            письмо первой подачи (архив)
│   ├── response_to_reviewers.{md,docx}   постраничный ответ рецензентам
│   ├── EM_reply_boxes.md                 текст для полей Reply to comment
│   ├── Highlights.docx, highlights.txt
│   ├── title_for_editorial_manager.txt   заголовок одной строкой
│   ├── README_submission.md              полный журнал правок
│   └── TODO_BEFORE_SUBMIT.md             что осталось сделать
│
├── code/                  ЕДИНСТВЕННАЯ папка, уходящая в Git и Zenodo
├── zenodo/                zenodo_v1.2.0.zip — запасной путь загрузки
├── reviews/               отзывы и аудиты, локально
├── git/PUSH_COMMANDS.md   команды публикации — только код
└── archive/               первая подача, шаблоны elsarticle, старые сборки
```

## Пересборка статьи

```
pdflatex article && bibtex article && pdflatex article && pdflatex article
cp article.pdf build/article.pdf
python3 make_docx.py article.tex build/article.docx
```

46 страниц, 0 ошибок, 0 неопределённых ссылок и цитат.
`article.tex` содержит `\graphicspath{{figures/}}`, поэтому рисунки берутся
из `figures/` и дублировать их в корень не нужно.

## Воспроизведение расчётов

```
cd code
python3 -m pip install -r requirements.txt
python3 terramechanics_model.py
```

Должны пройти девять аналитических проверок, а `results.json` совпасть с тем,
что лежит рядом.

## Правило публикации

Статья, ответы рецензентам и cover letter никогда не попадают в Git.
Репозиторий инициализируется внутри `code/`, а не в корне проекта. Запись на
Zenodo привязана к GitHub-репозиторию `Dev-Nikita/terramechanics-based`, то
есть в архив Zenodo попадает всё содержимое репозитория — ещё одна причина
держать там только код. Команды и проверки — в `git/PUSH_COMMANDS.md`.
