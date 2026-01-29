package com.refinedining.infra.publicdata;

import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;

@Slf4j
@Component
@RequiredArgsConstructor
public class PublicDataClient {

    private final RestTemplate restTemplate;

    @Value("${public-data.api-key}")
    private String apiKey;

    @Value("${public-data.base-url}")
    private String baseUrl;

    public PublicNutriResponse fetchNutriData(int page, int size) {
        // 인증키 인코딩 문제를 방지하기 위해 URI 객체로 직접 생성
        log.info("보내는 API KEY: [{}]", apiKey);
        URI uri = UriComponentsBuilder.fromHttpUrl(baseUrl)
                .queryParam("serviceKey", apiKey) // 환경 변수에서 가져온 키 주입
                .queryParam("type", "json")
                .queryParam("pageNo", page)
                .queryParam("numOfRows", size)
                .build(true) // 이미 인코딩된 키인 경우 이중 인코딩 방지
                .toUri();

        log.info("Requesting Public Data API to URI: {}", uri.toString());

        try {
            return restTemplate.getForObject(uri, PublicNutriResponse.class);
        } catch (Exception e) {
            log.error("API 호출 중 오류 발생: {}", e.getMessage());
            throw new RuntimeException("공공데이터 API 호출 실패");
        }
    }
}