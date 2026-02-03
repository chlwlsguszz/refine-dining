package com.refinedining.domain.food.raw.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
@Table(name = "raw_food_materials", indexes = {
        @Index(name = "idx_raw_food_cd", columnList = "foodCd")
})
public class RawFoodMaterial {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ==========================================
    // 1. 기본 식별 정보
    // ==========================================
    @Column(unique = true, nullable = false, length = 50)
    private String foodCd;             // 식품코드

    @Column(nullable = false)
    private String foodNm;             // 식품명

    private String dataCd;             // 데이터구분코드
    private String typeNm;             // 데이터구분명
    private String foodOriginCd;       // 식품기원코드
    private String foodOriginNm;       // 식품기원명

    // ==========================================
    // 2. 식품 분류 정보 (Lv3 ~ Lv7)
    // ==========================================
    private String foodLv3Cd; private String foodLv3Nm;
    private String foodLv4Cd; private String foodLv4Nm;
    private String foodLv5Cd; private String foodLv5Nm;
    private String foodLv6Cd; private String foodLv6Nm;
    private String foodLv7Cd; private String foodLv7Nm;

    // ==========================================
    // 3. 영양성분 정보 (25종 + 기준량)
    // ==========================================
    private String nutConSrtrQua;      // 영양성분함량기준량

    private Double enerc;   // 에너지(kcal)
    private Double water;   // 수분(g)
    private Double prot;    // 단백질(g)
    private Double fatce;   // 지방(g)
    private Double ash;     // 회분(g)
    private Double chocdf;  // 탄수화물(g)
    private Double sugar;   // 당류(g)
    private Double fibtg;   // 식이섬유(g)
    private Double ca;      // 칼슘(mg)
    private Double fe;      // 철(mg)
    private Double p;       // 인(mg)
    private Double k;       // 칼륨(mg)
    private Double nat;     // 나트륨(mg)
    private Double vitaRae; // 비타민 A(μg RAE)
    private Double retol;   // 레티놀(μg)
    private Double cartb;   // 베타카로틴(μg)
    private Double thia;    // 티아민(mg)
    private Double ribf;    // 리보플라빈(mg)
    private Double nia;     // 니아신(mg)
    private Double vitc;    // 비타민 C(mg)
    private Double vitd;    // 비타민 D(μg)
    private Double chole;   // 콜레스테롤(mg)
    private Double fasat;   // 포화지방산(g)
    private Double fatrn;   // 트랜스지방산(g)

    // ==========================================
    // 4. 메타데이터 및 출처 정보
    // ==========================================
    private String refuse;          // 폐기율(%)
    private String srcCd;           // 출처코드
    private String srcNm;           // 출처명
    private String cooCd;           // 원산지국코드
    private String cooNm;           // 원산지국명
    private String foodCooRgnNm;    // 원산지역명
    private String imptYn;          // 수입여부
    private String dataProdCd;      // 데이터생성방법코드
    private String dataProdNm;      // 데이터생성방법명
    private String crtYmd;          // 데이터생성일자
    private String prdCollCapMon;   // 생산·채취·포획월
    private String crtrYmd;         // 데이터기준일자
    private String insttCode;       // 제공기관코드
    private String insttNm;         // 제공기관기관명


    public void updateAllFields(RawFoodMaterial updated) {
        // 1. 기본 식별 정보 (식품코드는 고유값이므로 업데이트에서 제외하거나 필요시 포함)
        this.foodNm = updated.getFoodNm();
        this.dataCd = updated.getDataCd();
        this.typeNm = updated.getTypeNm();
        this.foodOriginCd = updated.getFoodOriginCd();
        this.foodOriginNm = updated.getFoodOriginNm();

        // 2. 식품 분류 정보
        this.foodLv3Cd = updated.getFoodLv3Cd();
        this.foodLv3Nm = updated.getFoodLv3Nm();
        this.foodLv4Cd = updated.getFoodLv4Cd();
        this.foodLv4Nm = updated.getFoodLv4Nm();
        this.foodLv5Cd = updated.getFoodLv5Cd();
        this.foodLv5Nm = updated.getFoodLv5Nm();
        this.foodLv6Cd = updated.getFoodLv6Cd();
        this.foodLv6Nm = updated.getFoodLv6Nm();
        this.foodLv7Cd = updated.getFoodLv7Cd();
        this.foodLv7Nm = updated.getFoodLv7Nm();

        // 3. 영양성분 정보
        this.nutConSrtrQua = updated.getNutConSrtrQua();
        this.enerc = updated.getEnerc();
        this.water = updated.getWater();
        this.prot = updated.getProt();
        this.fatce = updated.getFatce();
        this.ash = updated.getAsh();
        this.chocdf = updated.getChocdf();
        this.sugar = updated.getSugar();
        this.fibtg = updated.getFibtg();
        this.ca = updated.getCa();
        this.fe = updated.getFe();
        this.p = updated.getP();
        this.k = updated.getK();
        this.nat = updated.getNat();
        this.vitaRae = updated.getVitaRae();
        this.retol = updated.getRetol();
        this.cartb = updated.getCartb();
        this.thia = updated.getThia();
        this.ribf = updated.getRibf();
        this.nia = updated.getNia();
        this.vitc = updated.getVitc();
        this.vitd = updated.getVitd();
        this.chole = updated.getChole();
        this.fasat = updated.getFasat();
        this.fatrn = updated.getFatrn();

        // 4. 메타데이터 및 출처 정보
        this.refuse = updated.getRefuse();
        this.srcCd = updated.getSrcCd();
        this.srcNm = updated.getSrcNm();
        this.cooCd = updated.getCooCd();
        this.cooNm = updated.getCooNm();
        this.foodCooRgnNm = updated.getFoodCooRgnNm();
        this.imptYn = updated.getImptYn();
        this.dataProdCd = updated.getDataProdCd();
        this.dataProdNm = updated.getDataProdNm();
        this.crtYmd = updated.getCrtYmd();
        this.prdCollCapMon = updated.getPrdCollCapMon();
        this.crtrYmd = updated.getCrtrYmd();
        this.insttCode = updated.getInsttCode();
        this.insttNm = updated.getInsttNm();
    }

}