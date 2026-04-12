package com.refinedining.api.weight.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class WeightPredictRequest {

    @NotBlank(message = "식품명은 필수입니다.")
    private String foodName;

    /** 조리 방법 (예: 구운것, 삶은것). null이면 AI가 추측 */
    private String cookingMethod;

    @NotNull(message = "조리 전 중량(g)은 필수입니다.")
    @Positive(message = "중량은 0보다 커야 합니다.")
    private Double baseWeight;
}
