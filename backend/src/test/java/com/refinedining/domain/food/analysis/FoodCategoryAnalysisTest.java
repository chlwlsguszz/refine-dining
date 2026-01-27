package com.refinedining.domain.food.analysis;

import com.refinedining.infra.publicdata.PublicDataClient;
import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.stream.Collectors;

@SpringBootTest(
        classes = {
                PublicDataClient.class,
                TestRestTemplateConfig.class
        },
        properties = {
                "spring.autoconfigure.exclude=" +
                        "org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration," +
                        "org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration"
        }
)
@ActiveProfiles("test")
public class FoodCategoryAnalysisTest {
    @Autowired
    private PublicDataClient publicDataClient;

    @Test
    @DisplayName("식품 분류 체계 분석: 중분류(Lv5)와 대표식품명(Lv4) 구조 파악하기")
    void analyzeFoodCategories() {
        // 1. 데이터 가져오기 (분석용이므로 넉넉하게 3000건 정도 한 번에 요청)
        // 공공데이터 API가 한 번에 1000건 이상을 지원하는지 확인 필요 (보통 1000~9999 지원)
        int fetchSize = 4000;
        System.out.println("=== 데이터 요청 시작 (" + fetchSize + "건) ===");

        PublicNutriResponse response = publicDataClient.fetchNutriData(1, fetchSize);
        List<PublicNutriResponse.NutriItem> items = response.response().body().items();

        System.out.println("=== 데이터 수신 완료: " + items.size() + "건 ===");

        // 2. Lv5(중분류) 기준으로 그룹화하여 Lv4(대표식품명) 모아보기
        // Map<중분류, Set<대표식품명>> 구조
        Map<String, Set<String>> categoryMap = items.stream()
                .collect(Collectors.groupingBy(
                        item -> getSafeString(item.foodLv5Nm()), // Key: 중분류
                        Collectors.mapping(
                                item -> getSafeString(item.foodLv4Nm()), // Value: 대표식품명 추출
                                Collectors.toSet() // 중복 제거해서 Set으로 수집
                        )
                ));

        // 3. 콘솔에 예쁘게 출력하기
        System.out.println("\n========== [분석 결과] 식품 분류 계층 구조 ==========\n");

        // 중분류 이름 순으로 정렬해서 출력
        categoryMap.keySet().stream().sorted().forEach(lv5 -> {
            Set<String> lv4Set = categoryMap.get(lv5);

            System.out.println("📂 중분류(Lv5): [" + lv5 + "]");
            System.out.println("   └─ 📄 대표식품명(Lv4) 목록 (" + lv4Set.size() + "개):");

            // 대표식품명도 정렬해서 출력
            lv4Set.stream().sorted().forEach(lv4 -> {
                System.out.println("      - " + lv4);
            });
            System.out.println("--------------------------------------------------");
        });
    }

    // null 값 방지용 헬퍼 메서드
    private String getSafeString(String value) {
        return (value == null || value.isBlank()) ? "(분류없음)" : value.trim();
    }

    @Test
    @DisplayName("공공데이터 전체 개수 확인") //결과 : 3672건
    void checkTotalCount() {
        // 1페이지에 딱 1개만 요청 (메타데이터만 확인 목적)
        PublicNutriResponse response = publicDataClient.fetchNutriData(1, 1);

        if (response != null && response.response().body() != null) {
            int totalCount = response.response().body().totalCount();
            System.out.println("========================================");
            System.out.println("📊 공공데이터 전체 레코드 수: " + totalCount + "건");
            System.out.println("========================================");
        } else {
            System.out.println("응답을 받아오지 못했습니다.");
        }
    }
}


