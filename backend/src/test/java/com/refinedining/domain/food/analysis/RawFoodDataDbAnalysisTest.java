package com.refinedining.domain.food.analysis;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.*;

@SpringBootTest
@ActiveProfiles("test")

public class RawFoodDataDbAnalysisTest {

    @Autowired
    private RawFoodMaterialRepository rawFoodMaterialRepository;

    @Test
    @DisplayName("DB 데이터 분석: 출처별 분류 레벨 보유 현황")
    void analyzeCategoryLevelsBySource() {
        // 1. DB 조회
        List<RawFoodMaterial> allItems = rawFoodMaterialRepository.findAll();
        System.out.println("=== DB 데이터 로드 완료: " + allItems.size() + "건 ===");

        if (allItems.isEmpty()) {
            System.out.println("⚠️ DB가 비어있습니다. DataInitializer를 통해 데이터를 먼저 적재해주세요.");
            return;
        }

        // 2. 집계
        Map<String, CategoryBucket> result = new LinkedHashMap<>();

        for (RawFoodMaterial item : allItems) {
            String sourceKey = safe(item.getSrcNm());
            CategoryBucket bucket = result.computeIfAbsent(sourceKey, k -> new CategoryBucket());

            bucket.lv4.add(safe(item.getFoodLv4Nm()));
            bucket.lv5.add(safe(item.getFoodLv5Nm()));
            bucket.lv6.add(safe(item.getFoodLv6Nm()));
            bucket.lv7.add(safe(item.getFoodLv7Nm()));
        }

        // 3. 출력
        System.out.println("\n========== [DB 기준 분석 결과] ==========\n");
        result.forEach((source, bucket) -> {
            System.out.println("출처: " + source);
            System.out.println("   - 대표식품명(Lv4): " + bucket.lv4.size() + "종");
            System.out.println("   - 식품중분류(Lv5): " + bucket.lv5.size() + "종");
            System.out.println("   - 식품소분류(Lv6): " + bucket.lv6.size() + "종");
            System.out.println("   - 식품세분류(Lv7): " + bucket.lv7.size() + "종");
            System.out.println("-------------------------------------------");
        });
    }

    @Test
    @DisplayName("DB 데이터 분석: 세분류코드 매핑 CSV 내보내기")
    void exportLv7MappingToCsv() {
        List<RawFoodMaterial> allItems = rawFoodMaterialRepository.findAll();
        if (allItems.isEmpty()) return;

        Map<String, String> codeMap = new TreeMap<>();
        for (RawFoodMaterial item : allItems) {
            String code = item.getFoodLv7Cd();
            String name = item.getFoodLv7Nm();
            if (code != null && !code.isBlank() && !code.equals("-")) {
                codeMap.put(code, name);
            }
        }

        String fileName = "db_food_lv7_analysis.csv";
        File file = new File(fileName);

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(file))) {
            writer.write("식품세분류코드,식품세분류명");
            writer.newLine();

            for (Map.Entry<String, String> entry : codeMap.entrySet()) {
                writer.write(entry.getKey() + "," + entry.getValue());
                writer.newLine();
            }
            System.out.println("CSV 파일 생성 완료: " + file.getAbsolutePath());
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // --- Helpers ---
    static class CategoryBucket {
        Set<String> lv4 = new TreeSet<>();
        Set<String> lv5 = new TreeSet<>();
        Set<String> lv6 = new TreeSet<>();
        Set<String> lv7 = new TreeSet<>();
    }

    private String safe(String value) {
        return (value == null || value.isBlank()) ? "(없음)" : value.trim();
    }
}