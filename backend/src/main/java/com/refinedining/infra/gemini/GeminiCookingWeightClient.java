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

    @Value("${gemini.api-key}")
    private String apiKey;

    @Value("${gemini.base-url}")
    private String baseUrl;

    @Value("${gemini.model:gemini-2.5-flash}")
    private String model;

    public GeminiCookingWeightClient(@Qualifier("aiRestTemplate") RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * 조리 전 중량(g)을 기준으로 조리 후 예상 중량(g)을 Gemini API로 요청합니다.
     *
     * @param foodName     식품명 (예: 삼겹살, 닭가슴살)
     * @param cookingMethod 조리 방법 설명 (예: 구운것, 삶은것) - null이면 AI가 추측
     * @param baseWeightG   조리 전 중량(g)
     * @return 조리 후 예상 중량(g)
     */
    public double predictWeightAfterCooking(String foodName, String cookingMethod, double baseWeightG) {
        log.info("[Gemini API 호출] foodName={}, cookingMethod={}, baseWeight={}g, model={}",
                foodName, cookingMethod, baseWeightG, model);

        String prompt = buildPrompt(foodName, cookingMethod, baseWeightG);
        String url = baseUrl + "/models/" + model + ":generateContent?key=" + apiKey;

        Map<String, Object> requestBody = Map.of(
                "contents", List.of(Map.of(
                        "parts", List.of(Map.of("text", prompt))
                )),
                "generationConfig", Map.of(
                        "temperature", 0.0,
                        "maxOutputTokens", 64
                )
        );

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    new ParameterizedTypeReference<Map<String, Object>>() {}
            );

            String text = extractTextFromResponse(response.getBody());
            double predicted = parseNumericResponse(text, baseWeightG);
            log.info("[Gemini API 응답] foodName={}, rawResponse={}, predictedWeight={}g",
                    foodName, (text != null && !text.isBlank() ? text : "(empty)"), predicted);
            return predicted;
        } catch (Exception e) {
            log.error("Gemini API 호출 실패: foodName={}, cookingMethod={}", foodName, cookingMethod, e);
            throw new RuntimeException("AI 예측 중 오류가 발생했습니다.");
        }
    }

    private String buildPrompt(String foodName, String cookingMethod, double baseWeightG) {
        StringBuilder sb = new StringBuilder();
        sb.append("너는 조리 후 중량을 추정하는 전문가다. ");
        sb.append("식품을 조리하면 수분·지방 손실 등으로 중량이 줄어든다.\n\n");
        sb.append("입력:\n");
        sb.append("- 식품명: ").append(foodName).append("\n");
        sb.append("- 조리 전 중량: ").append(String.format("%.0f", baseWeightG)).append("g\n");
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

    private double parseNumericResponse(String text, double fallback) {
        if (text == null || text.isBlank()) {
            log.warn("Gemini 응답이 비어있음. 기본값 사용: {}", fallback);
            return fallback * 0.7;
        }

        Matcher m = NUMBER_PATTERN.matcher(text);
        if (m.find()) {
            try {
                double value = Double.parseDouble(m.group());
                return Math.max(0, Math.min(value, 10000)); // 0 ~ 10000g 범위 제한
            } catch (NumberFormatException e) {
                log.warn("숫자 파싱 실패: text={}", text);
            }
        }

        log.warn("응답에서 숫자를 찾지 못함: text={}. 기본값 사용.", text);
        return fallback * 0.7;
    }
}
