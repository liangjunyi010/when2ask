on run argv
  set deckPath to item 1 of argv
  tell application "Microsoft PowerPoint"
    set p to presentation "Native_Validation_Copy.pptx"
    set n to count slides of p
    set mediaShape to shape "Embedded synchronized Jev replay" of slide 9 of p
    set autoPlay to play on entry of animation play settings of animation settings of mediaShape
    set ss to slide show settings of p
    set starting slide of ss to 9
    set ending slide of ss to 9
    set range type of ss to slide show range
    set w to run slide show ss
    set v to slideshow view of w
    set playerObject to get player from v for mediaShape
    delay 2
    set firstPosition to current position of playerObject
    delay 2
    set secondPosition to current position of playerObject
    exit slide show v
    set answer to "{\"application\":\"Microsoft PowerPoint\",\"version\":\"" & version & "\",\"slides\":" & n & ",\"play_on_entry\":" & autoPlay & ",\"player_positions_ms\":[" & firstPosition & "," & secondPosition & "],\"slide_show_exited\":true}"
    close p saving no
    return answer
  end tell
end run
