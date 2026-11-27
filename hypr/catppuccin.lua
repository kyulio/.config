-- catppuccin.lua (Monochrome Grayscale Theme matching Black & White Rose Wallpaper)
-- 전체 색상 스키마를 칠흑 같은 블랙, 차콜 그레이, 실버 화이트로 세련되게 통일했습니다.

local cp = {
    -- 톤다운된 미색 / 실버 텍스트 계열
    text      = 0xffffffff, -- 순백색 텍스트
    subtext1  = 0xffdddddd, -- 밝은 실버 그레이
    subtext0  = 0xffaaaaaa, -- 차분한 라이트 그레이
    overlay2  = 0xff888888, -- 미디엄 그레이
    overlay1  = 0xff666666, -- 어두운 실버
    overlay0  = 0xff444444, -- 차콜 그레이
    
    -- 깊고 어두운 블랙 & 차콜 배경/표면 계열
    surface2  = 0xff333333,
    surface1  = 0xff222222,
    surface0  = 0xff111111,
    base      = 0xff000000, -- 배경화면과 동일한 칠흑색
    mantle    = 0xff0a0a0a, -- 비활성 테두리/어두운 악센트
    crust     = 0xff050505,

    -- 차분하고 세련된 악센트 컬러 (그레이 스케일)
    sapphire  = 0xffffffff, -- 활성 테두리 메인 (순백색)
    lavender  = 0xff888888, -- 활성 테두리 서브 (차분한 그레이)
    blue      = 0xffcccccc, -- 실버
    sky       = 0xffdddddd,
    teal      = 0xffbbbbbb,
    green     = 0xffe0e0e0,
    yellow    = 0xffb8b8b8,
    peach     = 0xffdcdcdc,
    maroon    = 0xffefefef,
    red       = 0xffa0a0a0,
    mauve     = 0xffcccccc,
    flamingo  = 0xffdcdcdc,
    rosewater = 0xffffffff,
}

return cp

