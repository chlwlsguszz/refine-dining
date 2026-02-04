package com.refinedining.domain.food.refined.dto;

import com.refinedining.domain.food.refined.entity.FoodMaterial;

public record FoodChildResponse(
        Long id,
        String name,
        String cookingMethod,
        Double calories,
        Double protein,
        Double fat,
        Double carbohydrate,
        Double sugar,
        Double sodium
) {
    public static FoodChildResponse from(FoodMaterial entity) {
        return new FoodChildResponse(
                entity.getId(),
                entity.getName(),
                entity.getCookingMethod(),
                entity.getCalories(),
                entity.getProtein(),
                entity.getFat(),
                entity.getCarbohydrate(),
                entity.getSugar(),
                entity.getSodium()
        );
    }
}
