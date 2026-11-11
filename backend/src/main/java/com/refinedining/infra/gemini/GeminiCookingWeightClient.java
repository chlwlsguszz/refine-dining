package com.refinedining.infra.gemini;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;
import java.util.OptionalDouble;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Google Gemini API를 호출하여 조리 후 예상 중량(g)을 예측합니다.
 */
@Slf4j
@Component
public class GeminiCookingWeightClient {

    private static final Pattern NUMBER_PATTERN = Pattern.compile("-?\\d+\\.?\\d*");

    private final RestTemplate restTemplate;
    private final Map<String, Double> ratioCache = new ConcurrentHashMap<>();

    @Value("${gemini.api-key:}")
    private String apiKey;

    @Value("${gemini.base-url:https://generativelanguage.googleapis.com/v1beta}")
    private String baseUrl;

    @Value("${gemini.model:gemini-2.5-flash}")
    private String model;

    public GeminiCookingWeightClient(@Qualifier("aiRestTemplate") RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * 조리 전 중량(g)을 기준으로 조리 후 예상 중량(g)을 Gemini API로 요청합니다.
     */
    public double predictWeightAfterCooking(String foodName, String cookingMethod, double baseWeightG) {
        OptionalDouble aiPredicted = tryPredictWeight(foodName, cookingMethod, baseWeightG);
        return aiPredicted.orElseGet(() -> Math.round(baseWeightG * defaultYieldRatio(cookingMethod) * 10.0) / 10.0);
    }

    /**
     * Gemini API를 통해 조리 후 예상 중량(g)을 예측하며, 성공 시 값을 담은 OptionalDouble을 반환합니다.
     * 동일 (식품명, 조리방법)에 대해서는 수율 비율(ratio)을 캐싱하여 재사용합니다.
     */
    public OptionalDouble tryPredictWeight(String foodName, String cookingMethod, double baseWeightG) {
        if (baseWeightG <= 0) {
            return OptionalDouble.empty();
        }

        String cacheKey = (foodName == null ? "" : foodName.trim()) + "::" + (cookingMethod == null ? "" : cookingMethod.trim());
        Double cachedRatio = ratioCache.get(cacheKey);
        if (cachedRatio != null) {
            double cachedWeight = Math.round(baseWeightG * cachedRatio * 10.0) / 10.0;
            log.debug("[Gemini 캐시 히트] key={}, ratio={}, predictedWeight={}g", cacheKey, cachedRatio, cachedWeight);
            return OptionalDouble.of(cachedWeight);
        }

        if (apiKey == null || apiKey.isBlank()) {
            log.warn("Gemini API 키가 설정되지 않아 AI 호출을 건너뜁니다.");
            return OptionalDouble.empty();
        }

        log.info("[Gemini API 호출] foodName={}, cookingMethod={}, baseWeight={}g, model={}",
                foodName, cookingMethod, baseWeightG, model);

        String prompt = buildPrompt(foodName, cookingMethod, baseWeightG);
        String url = baseUrl + "/models/" + model + ":generateContent";

        // Gemini 2.5 계열에서 thinking 토큰이 maxOutputTokens를 소진하여 빈 응답이 오는 현상을 방지하기 위해 thinkingBudget=0 설정
        Map<String, Object> requestBody = Map.of(
                "contents", List.of(Map.of(
                        "parts", List.of(Map.of("text", prompt))
                )),
                "generationConfig", Map.of(
                        "temperature", 0.0,
                        "maxOutputTokens", 128,
                        "thinkingConfig", Map.of("thinkingBudget", 0)
                )
        );

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("x-goog-api-key", apiKey);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    new ParameterizedTypeReference<Map<String, Object>>() {}
            );

            String text = extractTextFromResponse(response.getBody());
            OptionalDouble parsed = parseNumericResponse(text);
            if (parsed.isPresent()) {
                double predicted = parsed.getAsDouble();
                double ratio = predicted / baseWeightG;
                if (ratio >= 0.1 && ratio <= 4.0) {
                    ratioCache.put(cacheKey, ratio);
                }
                log.info("[Gemini API 응답] foodName={}, rawResponse={}, predictedWeight={}g",
                        foodName, text, predicted);
                return OptionalDouble.of(predicted);
            }
            log.warn("[Gemini API 빈 응답 또는 숫자 추출 실패] foodName={}, rawResponse={}", foodName, text);
            return OptionalDouble.empty();
        } catch (Exception e) {
            log.error("Gemini API 호출 실패: foodName={}, cookingMethod={}, error={}", foodName, cookingMethod, e.getMessage());
            return OptionalDouble.empty();
        }
    }

    public double defaultYieldRatio(String cookingMethod) {
        if (cookingMethod == null) return 0.75;
        return switch (cookingMethod.trim()) {
            case "구운것" -> 0.72;
            case "튀긴것" -> 0.75;
            case "볶은것" -> 0.78;
            case "조린것" -> 0.80;
            case "삶은것" -> 0.85;
            case "찐것" -> 0.88;
            case "데친것" -> 0.90;
            case "전자레인지로 가열한것" -> 0.82;
            case "생것" -> 1.0;
            default -> 0.75;
        };
    }

    private String buildPrompt(String foodName, String cookingMethod, double baseWeightG) {
        StringBuilder sb = new StringBuilder();
        sb.append("너는 조리 후 중량을 추정하는 식품영양 전문가다. ");
        sb.append("식품을 조리하면 수분 증발·지방 용출 또는 수분 흡수 등으로 중량이 변한다.\n\n");
        sb.append("입력:\n");
        sb.append("- 식품명: ").append(foodName).append("\n");
        sb.append("- 조리 전 중량: ").append(String.format("%.1f", baseWeightG)).append("g\n");
        if (cookingMethod != null && !cookingMethod.isBlank()) {
            sb.append("- 조리 방법: ").append(cookingMethod).append("\n");
        }
        sb.append("\n위 조건에서 조리 후 예상 중량(g)을 숫자 하나만 답해라. 소수점 한 자리까지. 예: 68.4\n");
        sb.append("단위(g), 설명, 문장 없이 숫자만 출력해라.");
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private String extractTextFromResponse(Map<String, Object> body) {
        if (body == null) return "";

        List<Map<String, Object>> candidates = (List<Map<String, Object>>) body.get("candidates");
        if (candidates == null || candidates.isEmpty()) return "";

        Map<String, Object> content = (Map<String, Object>) candidates.get(0).get("content");
        if (content == null) return "";

        List<Map<String, Object>> parts = (List<Map<String, Object>>) content.get("parts");
        if (parts == null || parts.isEmpty()) return "";

        Object text = parts.get(0).get("text");
        return text != null ? text.toString().trim() : "";
    }

    private OptionalDouble parseNumericResponse(String text) {
        if (text == null || text.isBlank()) {
            return OptionalDouble.empty();
        }

        Matcher m = NUMBER_PATTERN.matcher(text);
        if (m.find()) {
            try {
                double value = Double.parseDouble(m.group());
                if (value > 0 && value <= 100000) {
                    return OptionalDouble.of(Math.round(value * 10.0) / 10.0);
                }
            } catch (NumberFormatException e) {
                log.warn("숫자 파싱 실패: text={}", text);
            }
        }
        return OptionalDouble.empty();
    }
}
