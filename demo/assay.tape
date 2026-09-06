# The short version: what the docs say, what assay finds, what is actually
# on disk. Rendered with vhs (github.com/charmbracelet/vhs):
#
#   vhs demo/assay.tape
#
# Everything here runs live. Nothing is replayed from a saved transcript.

Output demo/assay.gif

Set Shell bash
Set FontSize 15
Set Width 1300
Set Height 620
Set Padding 22
Set Theme "Catppuccin Mocha"
Set TypingSpeed 32ms

Hide
Type "cd '/Users/bipinrimal/Downloads/claude work/assay'" Enter
Type "export PS1='$ '" Enter
Type "clear" Enter
Show

Sleep 1s

# --- 1. the line as it appears on the published install page ---
Type "sed -n '54,58p' corpus/pg_tde/documentation/docs/apt.md"
Sleep 500ms
Enter
Sleep 3s

Type "# paste that into a shell and see what happens"
Sleep 400ms
Enter
Sleep 800ms

Type "bash -c 'sudo apt-get install -y percona-pg-tde(pg-version)'"
Sleep 500ms
Enter
Sleep 3s

Type "clear" Enter
Sleep 500ms

# --- 2. the static half, over the whole doc set ---
Type "assay lint corpus/pg_tde/documentation/docs --expect-major 18 | head -32"
Sleep 500ms
Enter
Sleep 7s

Type "clear" Enter
Sleep 500ms

# --- 3. the feature itself, on disk ---
Type "# the extension works. the same row, in a plain table and a tde_heap table:"
Sleep 400ms
Enter
Sleep 800ms

Type "./demo/prove-encryption.sh"
Sleep 500ms
Enter
Sleep 6s

Type "# one row. readable in one raw heap file, absent from the other."
Sleep 400ms
Enter
Sleep 3s
