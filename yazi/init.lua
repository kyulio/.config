-- 둥근 테두리
require("full-border"):setup { set = "rounded" }

-- 파일 옆에 git 상태 표시
require("git"):setup { order = 1500 }

-- l / Enter 로 여러 파일 선택 시 한꺼번에 열기
require("smart-enter"):setup { open_multi = true }
