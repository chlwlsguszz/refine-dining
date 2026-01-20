package com.refinedining.domain.food.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class FoodMaterial {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String foodGroup;      // 예: '고등어', '삼겹살'
    private String name;           // 예: '고등어, 대서양, 생것'
    private String processingState; // 'RAW', 'GRILLED', 'BOILED' 등

    // 100g 당 함량
    private Double protein;
    private Double fat;
    private Double calories;
    private Double carbohydrate;

    @Builder
    public FoodMaterial(String foodGroup, String name, String processingState, Double protein, Double fat, Double calories, Double carbohydrate) {
        this.foodGroup = foodGroup;
        this.name = name;
        this.processingState = processingState;
        this.protein = protein;
        this.fat = fat;
        this.calories = calories;
        this.carbohydrate = carbohydrate;
    }
}