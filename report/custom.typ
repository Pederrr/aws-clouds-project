#show link: set text(fill: rgb("#b11226"))
#show link: underline

#show quote: set pad(left: 1.5em)
#show quote: it => {
  stack(
    dir: ltr,
    spacing: 0.8em,
    rect(width: 2pt, fill: rgb("#cccccc"), stroke: none),
    emph(it)
  )
}
