package com.refinedining.domain.food.refined.dto;

import com.refinedining.domain.food.refined.entity.FoodMaterial;

public record FoodCompareResponse(
        FoodSearchResponse parentData,
        FoodChildResponse childData
) {
    public static FoodCompareResponse of(FoodMaterial parent, FoodMaterial child) {
        return new FoodCompareResponse(
                FoodSearchResponse.from(parent),
                FoodChildResponse.from(child)
        );
    }
}
