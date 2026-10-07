// 상호 연결할 사이트 목록 (동일 단계의 대등한 사이트). 현재 사이트는 메뉴에서 제외된다.
window.SITE_CONFIG = {
  // 화면 표시 단위: 원/㎥. 원자료(원/MJ)에 아래 발열량을 적용해 환산한다. (1 kcal = 4.1868 kJ)
  heatingValueKcal: 10190,
  current: "energy-price",
  sites: [
    { id: "energy-index", name: "에너지 시장 주요정보", url: "https://shycrt-lgtm.github.io/Energy-Index/" },
    { id: "kpx-daily", name: "전력시장 전일실적", url: "https://shycrt-lgtm.github.io/KPX-Daily-Report/" },
    { id: "tms", name: "TMS", url: "https://shycrt-lgtm.github.io/TMS/" },
    { id: "energy-price", name: "에너지 요금 현황", url: "https://shycrt-lgtm.github.io/Energy-Price/" }
  ]
};
