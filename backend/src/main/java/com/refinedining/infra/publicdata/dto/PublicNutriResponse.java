package com.refinedining.infra.publicdata.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record PublicNutriResponse(Response response) {
    public record Response(Header header, Body body) {}
    public record Header(String resultCode, String resultMsg) {}
    public record Body(List<NutriItem> items, int totalCount) {}

    public record NutriItem(
            // ==========================================
            // 1. 기본 식별 정보
            // ==========================================
            @JsonProperty("foodCd") String foodCd,             // 식품코드
            @JsonProperty("foodNm") String foodNm,             // 식품명
            @JsonProperty("dataCd") String dataCd,             // 데이터구분코드
            @JsonProperty("typeNm") String typeNm,             // 데이터구분명
            @JsonProperty("foodOriginCd") String foodOriginCd, // 식품기원코드
            @JsonProperty("foodOriginNm") String foodOriginNm, // 식품기원명

            // ==========================================
            // 2. 식품 분류 정보 (Lv3 ~ Lv7)
            // ==========================================
            @JsonProperty("foodLv3Cd") String foodLv3Cd, // 식품대분류코드
            @JsonProperty("foodLv3Nm") String foodLv3Nm, // 식품대분류명
            @JsonProperty("foodLv4Cd") String foodLv4Cd, // 대표식품코드
            @JsonProperty("foodLv4Nm") String foodLv4Nm, // 대표식품명
            @JsonProperty("foodLv5Cd") String foodLv5Cd, // 식품중분류코드
            @JsonProperty("foodLv5Nm") String foodLv5Nm, // 식품중분류명
            @JsonProperty("foodLv6Cd") String foodLv6Cd, // 식품소분류코드
            @JsonProperty("foodLv6Nm") String foodLv6Nm, // 식품소분류명
            @JsonProperty("foodLv7Cd") String foodLv7Cd, // 식품세분류코드
            @JsonProperty("foodLv7Nm") String foodLv7Nm, // 식품세분류명

            // ==========================================
            // 3. 영양성분 정보 (총 25종 + 기준량)
            // ==========================================
            @JsonProperty("nutConSrtrQua") String nutConSrtrQua, // 영양성분함량기준량
            @JsonProperty("enerc") String enerc,       // 에너지(kcal)
            @JsonProperty("water") String water,       // 수분(g)
            @JsonProperty("prot") String prot,         // 단백질(g)
            @JsonProperty("fatce") String fatce,       // 지방(g)
            @JsonProperty("ash") String ash,           // 회분(g)
            @JsonProperty("chocdf") String chocdf,     // 탄수화물(g)
            @JsonProperty("sugar") String sugar,       // 당류(g)
            @JsonProperty("fibtg") String fibtg,       // 식이섬유(g)
            @JsonProperty("ca") String ca,             // 칼슘(mg)
            @JsonProperty("fe") String fe,             // 철(mg)
            @JsonProperty("p") String p,               // 인(mg)
            @JsonProperty("k") String k,               // 칼륨(mg)
            @JsonProperty("nat") String nat,           // 나트륨(mg)
            @JsonProperty("vitaRae") String vitaRae,   // 비타민 A(μg RAE)
            @JsonProperty("retol") String retol,       // 레티놀(μg)
            @JsonProperty("cartb") String cartb,       // 베타카로틴(μg)
            @JsonProperty("thia") String thia,         // 티아민(mg)
            @JsonProperty("ribf") String ribf,         // 리보플라빈(mg)
            @JsonProperty("nia") String nia,           // 니아신(mg)
            @JsonProperty("vitc") String vitc,         // 비타민 C(mg)
            @JsonProperty("vitd") String vitd,         // 비타민 D(μg)
            @JsonProperty("chole") String chole,       // 콜레스테롤(mg)
            @JsonProperty("fasat") String fasat,       // 포화지방산(g)
            @JsonProperty("fatrn") String fatrn,       // 트랜스지방산(g)

            // ==========================================
            // 4. 메타데이터 및 출처 정보
            // ==========================================
            @JsonProperty("refuse") String refuse,             // 폐기율(%)
            @JsonProperty("srcCd") String srcCd,               // 출처코드
            @JsonProperty("srcNm") String srcNm,               // 출처명
            @JsonProperty("cooCd") String cooCd,               // 원산지국코드
            @JsonProperty("cooNm") String cooNm,               // 원산지국명
            @JsonProperty("foodCooRgnNm") String foodCooRgnNm, // 원산지역명
            @JsonProperty("imptYn") String imptYn,             // 수입여부
            @JsonProperty("dataProdCd") String dataProdCd,     // 데이터생성방법코드
            @JsonProperty("dataProdNm") String dataProdNm,     // 데이터생성방법명
            @JsonProperty("crtYmd") String crtYmd,             // 데이터생성일자
            @JsonProperty("prdCollCapMon") String prdCollCapMon, // 생산·채취·포획월
            @JsonProperty("crtrYmd") String crtrYmd,           // 데이터기준일자
            @JsonProperty("instt_code") String insttCode,      // 제공기관코드 (snake_case -> camelCase 매핑)
            @JsonProperty("instt_nm") String insttNm           // 제공기관기관명
    ) {}
}