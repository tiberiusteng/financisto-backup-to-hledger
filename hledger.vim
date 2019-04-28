if version < 600
  syntax clear
elseif exists("b:current_sytax")
  finish
endif

syn match hledgerComment /;.\+/

syn match hledgerDate /^\d\{4}-\d\{2}-\d\{2}/ nextgroup=hledgerStatus,hledgerPayee,hledgerDesc

syn match hledgerDesc /[^;]\+/ contained

syn match hledgerAccount /\s\+\([^ ;]\| [^ ;]\)\+/ contained

syn match hledgerPayee / [^!*|]\+|/he=e-1 contained nextgroup=hledgerDesc

syn match hledgerStatus / [!*]/ contained nextgroup=hledgerPayee,hledgerDesc
syn match hledgerPostingStatus / [!*]/ contained nextgroup=hledgerAccount

syn match hledgerPosting /^\s\@=/ nextgroup=hledgerPostingStatus,hledgerAccount

syn match hledgerNegativeAmount / -[0-9,.]\+/
syn match hledgerPositiveAmount / [0-9,.]\+/

highlight default link hledgerComment Comment
highlight default link hledgerDesc Ignore
highlight default link hledgerPayee Type
highlight default link hledgerDate Constant
highlight default link hledgerStatus PreProc
highlight default link hledgerPostingStatus PreProc
highlight default link hledgerAccount Identifier
highlight default hledgerPositiveAmount ctermfg=green guifg=green
highlight default hledgerNegativeAmount ctermfg=red guifg=red
