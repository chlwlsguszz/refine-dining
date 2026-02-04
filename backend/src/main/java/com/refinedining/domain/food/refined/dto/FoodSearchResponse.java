package com.refinedining.domain.food.refined.dto;

import com.refinedining.domain.food.refined.entity.FoodMaterial;

import java.util.List;

public record FoodSearchResponse(
        Long id,
        String name,
        String foodCd,
        Double calories,
        Double protein,
        Double fat,
        Double carbohydrate,
        Double sugar,
        Double sodium,
        List<FoodChildResponse> cookingMethods
) {
    public static FoodSearchResponse from(FoodMaterial entity) {
        return new FoodSearchResponse(
                entity.getId(),
                entity.getName(),
                entity.getCookingMethod(),
                entity.getCalories(),
                entity.getProtein(),
                entity.getFat(),
                entity.getCarbohydrate(),
                entity.getSugar(),
                entity.getSodium(),
                entity.getChildren().stream()
                        .map(FoodChildResponse::from)
                        .toList()
        );
    }
}

