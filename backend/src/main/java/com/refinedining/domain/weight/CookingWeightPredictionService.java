package com.refinedining.domain.weight;

import com.refinedining.api.weight.dto.WeightPredictRequest;
import com.refinedining.api.weight.dto.WeightPredictResponse;
import com.refinedining.infra.gemini.GeminiCookingWeightClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.OptionalDouble;

@Slf4j
@Service
@RequiredArgsConstructor
public class CookingWeightPredictionService {

    private final GeminiCookingWeightClient geminiClient;

    /**
     * 조리 후 예상 중량(g)을 AI로 예측합니다. (하위 호환용)
     */
    public double predictWeightAfterCooking(String foodName, String cookingMethod, double baseWeightG) {
        return geminiClient.predictWeightAfterCooking(foodName, cookingMethod, baseWeightG);
    }

    /**
     * Gemini AI 예측과 공공데이터 영양성분(단백질 보존율) 기반 계산을 결합하여 조리 후 중량을 예측합니다.
     */
    public WeightPredictResponse predictHybrid(WeightPredictRequest request) {
        double baseWeight = request.getBaseWeight();
        String foodName = request.getFoodName();
        String cookingMethod = request.getCookingMethod();

        Double dataBasedWeight = calculateDataBasedWeight(baseWeight, request.getRawProtein(), request.getCookedProtein());
        OptionalDouble aiWeightOpt = geminiClient.tryPredictWeight(foodName, cookingMethod, baseWeight);

        double finalPredicted;
        String source;
        String explanation;

        if (aiWeightOpt.isPresent() && dataBasedWeight != null) {
            finalPredicted = aiWeightOpt.getAsDouble();
            source = "HYBRID";
            explanation = String.format("Gemini AI 예측(%.1fg)과 공공데이터 단백질 농축비 기반 추정(%.1fg)을 함께 비교했습니다.",
                    finalPredicted, dataBasedWeight);
        } else if (aiWeightOpt.isPresent()) {
            finalPredicted = aiWeightOpt.getAsDouble();
            source = "AI";
            explanation = "Gemini AI가 식품 특성과 조리 방법에 따른 수분·지방 변화를 바탕으로 예측한 중량입니다.";
        } else if (dataBasedWeight != null) {
            finalPredicted = dataBasedWeight;
            source = "DATA_ONLY";
            explanation = "공공데이터의 원재료 대비 조리 후 단백질 농축 비율을 기반으로 계산한 예상 중량입니다.";
        } else {
            double defaultRatio = geminiClient.defaultYieldRatio(cookingMethod);
            finalPredicted = round1(baseWeight * defaultRatio);
            source = "FALLBACK";
            explanation = "조리 방법별 평균 수율(" + Math.round(defaultRatio * 100) + "%)을 적용한 추정치입니다.";
        }

        double yieldRatio = round2(finalPredicted / baseWeight);

        return WeightPredictResponse.builder()
                .predictedWeight(finalPredicted)
                .dataBasedWeight(dataBasedWeight)
                .yieldRatio(yieldRatio)
                .source(source)
                .explanation(explanation)
                .build();
    }

    /**
     * 조리 전후 단백질 보존 법칙:
     * 조리 전 총 단백질(baseWeight * rawProtein / 100) ≈ 조리 후 총 단백질(cookedWeight * cookedProtein / 100)
     * => cookedWeight ≈ baseWeight * (rawProtein / cookedProtein)
     */
    private Double calculateDataBasedWeight(double baseWeight, Double rawProtein, Double cookedProtein) {
        if (rawProtein == null || cookedProtein == null || rawProtein <= 0.5 || cookedProtein <= 0.5) {
            return null;
        }
        double ratio = rawProtein / cookedProtein;
        // 비정상적인 이상치(예: 부재료 첨가 등) 방어: 수율 0.30 ~ 2.50 범위만 유효한 단일 식재료 수율로 인정
        if (ratio < 0.30 || ratio > 2.50) {
            return null;
        }
        return round1(baseWeight * ratio);
    }

    private double round1(double value) {
        return Math.round(value * 10.0) / 10.0;
    }

    private double round2(double value) {
        return Math.round(value * 100.0) / 100.0;
    }
}
