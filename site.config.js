// 상호 연결할 사이트 목록 (동일 단계의 대등한 사이트).
// url 이 비어 있으면 메뉴에 '주소 미설정'으로 표시된다. 주소를 채우면 바로 링크된다.
window.SITE_CONFIG = {
  current: "energy-price",
  sites: [
    { id: "energy-index", name: "Energy-Index", url: "" },
    { id: "kpx-daily", name: "KPX-Daily-Report", url: "" },
    { id: "tms", name: "TMS", url: "" },
    { id: "energy-price", name: "Energy-Price", url: "https://shycrt-lgtm.github.io/Energy-Price/" }
  ]
};
