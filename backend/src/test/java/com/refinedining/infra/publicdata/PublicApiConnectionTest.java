package com.refinedining.infra.publicdata;

import com.refinedining.domain.food.repository.FoodMaterialRepository;
import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ActiveProfiles;


@SpringBootTest(
        // API 통신만 확인할 것이므로 DB 관련 설정은 굳이 띄우지 않습니다. (속도 향상)
        properties = {
                "spring.autoconfigure.exclude=" +
                        "org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration," +
                        "org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration"
        }
)
@ActiveProfiles("test")
public class PublicApiConnectionTest {

    @Autowired
    private PublicDataClient publicDataClient;

    @MockBean
    private FoodMaterialRepository foodMaterialRepository;

    @Test
    @DisplayName("📡 API 연결 확인: 공공데이터 전체 개수 조회")
    void checkTotalCount() {
        System.out.println(">>> 외부 API 상태 점검을 시작합니다...");

        // 1페이지에 1개만 요청하여 메타데이터(totalCount)만 빠르게 확인
        PublicNutriResponse response = publicDataClient.fetchNutriData(1, 1);

        if (response != null && response.response().body() != null) {
            int totalCount = response.response().body().totalCount();
            System.out.println("========================================");
            System.out.println("API 통신 성공!");
            System.out.println("현재 공공데이터 전체 레코드 수: " + totalCount + "건");
            System.out.println("========================================");
        } else {
            System.err.println("API 응답을 받아오지 못했습니다. (네트워크 혹은 API 키 확인 필요)");
        }
    }
}
