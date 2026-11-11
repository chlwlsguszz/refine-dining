package com.refinedining.infra.publicdata;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
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

            // 공공데이터 API 응답 헤더에 charset=UTF-8이 누락된 경우 ISO-8859-1로 깨지는 현상을 방지하기 위해 byte[]로 수신 후 UTF-8 디코딩
            ResponseEntity<byte[]> response = restTemplate.exchange(
                    uri,
                    HttpMethod.GET,
                    new HttpEntity<>(headers),
                    byte[].class
            );

            byte[] rawBytes = response.getBody();
            String body = rawBytes != null ? new String(rawBytes, StandardCharsets.UTF_8) : "";
            String trimmed = body.trim();

            // 공공데이터 API가 에러일 때 HTML을 주는 경우가 있어 파싱 전에 방어
            if (trimmed.startsWith("<")) {
                String preview = trimmed.replaceAll("\\s+", " ")
                        .replaceAll("(serviceKey=)[^&\"\\s]+", "$1***");
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
