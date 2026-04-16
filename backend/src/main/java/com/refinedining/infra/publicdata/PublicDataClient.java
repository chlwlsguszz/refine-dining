package com.refinedining.infra.publicdata;

import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.nio.charset.StandardCharsets;

@Slf4j
@Component
@RequiredArgsConstructor
public class PublicDataClient {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${public-data.api-key}")
    private String apiKey;

    @Value("${public-data.base-url}")
    private String baseUrl;

    public PublicNutriResponse fetchNutriData(int page, int size) {
        URI uri = UriComponentsBuilder.fromHttpUrl(baseUrl)
                .queryParam("serviceKey", apiKey) // 환경 변수에서 가져온 키 주입
                .queryParam("type", "json")
                .queryParam("pageNo", page)
                .queryParam("numOfRows", size)
                .build()
                .toUri();

        // serviceKey는 민감정보이므로 로그에서 마스킹
        String safeUri = uri.toString().replaceAll("(serviceKey=)[^&]+", "$1***");
        log.info("Requesting Public Data API to URI: {}", safeUri);

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setAccept(MediaType.parseMediaTypes("application/json, */*"));

            ResponseEntity<String> response = restTemplate.exchange(
                    uri,
                    HttpMethod.GET,
                    new HttpEntity<>(headers),
                    String.class
            );

            String body = response.getBody() != null ? response.getBody() : "";
            String trimmed = body.trim();

            // 공공데이터 API가 에러일 때 HTML을 주는 경우가 있어 파싱 전에 방어
            if (trimmed.startsWith("<")) {
                String preview = new String(body.getBytes(StandardCharsets.ISO_8859_1), StandardCharsets.UTF_8);
                preview = preview.replaceAll("\\s+", " ");
                preview = preview.replaceAll("(serviceKey=)[^&\"\\s]+", "$1***");
                if (preview.length() > 300) preview = preview.substring(0, 300) + "...";
                log.error("Public Data API returned HTML (likely error page). status={}, preview={}",
                        response.getStatusCode(), preview);
                throw new RuntimeException("공공데이터 API가 JSON이 아닌 응답(HTML)을 반환했습니다.");
            }

            return objectMapper.readValue(body, PublicNutriResponse.class);
        } catch (Exception e) {
            log.error("API 호출/파싱 중 오류 발생: {}", e.getMessage(), e);
            throw new RuntimeException("공공데이터 API 호출 실패");
        }
    }
}