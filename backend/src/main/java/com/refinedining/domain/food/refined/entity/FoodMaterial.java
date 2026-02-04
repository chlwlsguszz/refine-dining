package com.refinedining.domain.food.refined.entity;
import jakarta.persistence.*;
import lombok.*;

import java.util.ArrayList;
import java.util.List;

// Self-Referencing
// 같은 소분류코드를 가진 데이터끼리 부모-자식 관계
// 세분류코드가 01이면 Parent


@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
@Table(name = "food_materials", indexes = {
        @Index(name = "idx_parent_id", columnList = "parent_id"),
        @Index(name = "idx_food_name", columnList = "name")
})
public class FoodMaterial {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String foodCd;

    private String name;

    // --- 계층 구조 ---
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "parent_id")
    private FoodMaterial parent;

    // N+1에 주의
    @OneToMany(mappedBy = "parent", cascade = CascadeType.ALL)
    @Builder.Default
    private List<FoodMaterial> children = new ArrayList<>();

    // --- 상태 및 분류 ---
    private String foodLv6Cd;      // 그룹핑 기준 코드
    private String foodLv7Cd;        // 가공 코드 원본 (01, 50 등)
    private String cookingMethod; // 매핑된 한글명 (구운것, 튀긴것 등)

    // --- 영양 성분 (정제됨) ---
    private Double calories;
    private Double protein;
    private Double fat;
    private Double carbohydrate;
    private Double sugar;
    private Double sodium;

    // --- 연관 관계 편의 메서드 ---
    public void addChild(FoodMaterial child) {
        this.children.add(child);
        child.setParent(this);
    }

    private void setParent(FoodMaterial parent) {
        this.parent = parent;
    }
}