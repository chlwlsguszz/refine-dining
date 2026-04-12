package com.refinedining.api.weight.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class WeightPredictResponse {

    /** 조리 후 예상 중량(g) */
    private double predictedWeight;
}
