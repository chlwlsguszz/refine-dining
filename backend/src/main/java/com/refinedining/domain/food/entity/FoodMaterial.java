package com.refinedining.domain.food.entity;

import jakarta.persistence.*;
import lombok.*;
import java.util.ArrayList;
import java.util.List;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class FoodMaterial {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // 공공데이터의 고유 식별자 (모든 행이 각자의 코드를 가짐)
    @Column(unique = true, nullable = false)
    private String foodCd;

    @Column(nullable = false)
    private String foodNm;

    private String foodLv3Nm;
    private String nutConSrtrQua;

    // --- 주요 영양 성분 ---
    private Double enerc;
    private Double prot;
    private Double fatce;
    private Double chocdf;
    private Double sugar;
    private Double nat;

    private String srcNm;
    private String crtrYmd;


    // 계층형 구조 및 검색 최적화 필드
    // ==========================================

    // 1. 조리 방식 구분 (필수)
    // 예: "생것", "굽기", "튀기기", "삶기" 등의 값이 들어감
    @Column(nullable = false)
    private String cookingMethod;

    // 2. 검색 최적화 플래그 (Search Optimization)

    // "생것"(원재료) 데이터인지 식별
    @Builder.Default
    @Column(name = "is_master")
    private boolean isMaster = false;

    // 사용자 검색 노출 여부
    // (조건: isMaster == true이면서, 자식(조리된 데이터)이 1개 이상 있을 때 true)
    @Builder.Default
    @Column(name = "is_searchable")
    private boolean isSearchable = false;

    // 조리법 요약 (프론트엔드 라디오 버튼 생성용)
    // 예: "굽기,튀기기,삶기"
    private String availableMethods;

    // 3. 부모-자식 관계 (Self-Reference)
    // 조리된 데이터(자식)는 원본 데이터(부모)의 ID를 가짐
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_id")
    private FoodMaterial parent;

    // (선택사항) 부모 입장에서 자식들을 조회할 일이 있다면 추가 (양방향 매핑)
    // 검색 속도를 위해 보통은 availableMethods만 쓰고, 이건 생략하기도 함
    @Builder.Default
    @OneToMany(mappedBy = "parent", fetch = FetchType.LAZY)
    private List<FoodMaterial> children = new ArrayList<>();

    // --- 비즈니스 로직 메서드 (데이터 정제 시 사용) ---
    public void updateSearchInfo(boolean isSearchable, String availableMethods) {
        this.isSearchable = isSearchable;
        this.availableMethods = availableMethods;
    }
}