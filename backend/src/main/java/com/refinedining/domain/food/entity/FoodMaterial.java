package com.refinedining.domain.food.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class FoodMaterial {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String foodCd; // 식품코드

    @Column(nullable = false)
    private String foodNm; // 식품명

    private String foodLv3Nm; // 식품대분류명

    private String nutConSrtrQua; // 영양성분함량기준량

    // 주요 영양 성분 (단위 포함하여 저장하거나 Double로 관리)
    private Double enerc;  // 에너지(kcal)
    private Double prot;   // 단백질(g)
    private Double fatce;  // 지방(g)
    private Double chocdf; // 탄수화물(g)
    private Double sugar;  // 당류(g)
    private Double nat;    // 나트륨(mg)

    private String srcNm;    // 출처명
    private String crtrYmd;  // 데이터기준일자
}