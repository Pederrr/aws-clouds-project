# Markdown version of the report

The report can be exported to PDF using pandoc with typst:

```
pandoc --pdf-engine=typst \
    --include-in-header custom.typ \
    --pdf-engine-opt=--root=.. \
    project-report.md -o report.pdf
```
