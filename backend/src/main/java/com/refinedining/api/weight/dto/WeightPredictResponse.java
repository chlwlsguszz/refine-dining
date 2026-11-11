package com.refinedining.api.weight.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WeightPredictResponse {

    /** 조리 후 예상 중량(g) */
    private double predictedWeight;

    /** 공공데이터 영양소(단백질 농축비) 기반 추정 중량(g) - 계산 가능한 경우 제공 */
    private Double dataBasedWeight;

    /** 조리 전 대비 조리 후 중량 비율 (예: 0.72) */
    private Double yieldRatio;

    /** 예측 출처 (HYBRID, AI, DATA_ONLY, FALLBACK) */
    private String source;

    /** 예측 근거 설명 */
    private String explanation;

    public WeightPredictResponse(double predictedWeight) {
        this.predictedWeight = predictedWeight;
        this.source = "AI";
    }
}
