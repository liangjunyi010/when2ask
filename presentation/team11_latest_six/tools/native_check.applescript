tell application "Microsoft PowerPoint"
  set p to presentation "Latest_Six_QA_Copy.pptx"
  set n to count slides of p
  set m to shape "When2Ask 50 second live console demo" of slide 10 of p
  set autoPlay to play on entry of animation play settings of animation settings of m
  set ss to slide show settings of p
  set starting slide of ss to 10
  set ending slide of ss to 10
  set range type of ss to slide show range
  set w to run slide show ss
  set v to slideshow view of w
  set playerObject to get player from v for m
  delay 2
  set p1 to current position of playerObject
  delay 2
  set p2 to current position of playerObject
  exit slide show v
  set answer to "{\"application\":\"Microsoft PowerPoint\",\"version\":\"" & version & "\",\"slides\":" & n & ",\"play_on_entry\":" & autoPlay & ",\"player_positions_ms\":[" & p1 & "," & p2 & "],\"slide_show_exited\":true}"
  close p saving no
  return answer
end tell
