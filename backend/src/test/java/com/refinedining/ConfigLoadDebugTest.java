package com.refinedining;

import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;
import org.springframework.test.context.ActiveProfiles;

@Disabled("로컬 DB 설정 확인용 수동 테스트")
@SpringBootTest
@ActiveProfiles("test")
public class ConfigLoadDebugTest {

    @Autowired
    private Environment env;

    @Test
    void printConfig() {
        System.out.println("activeProfiles = " + String.join(",", env.getActiveProfiles()));
        System.out.println("spring.datasource.url = " + env.getProperty("spring.datasource.url"));
        System.out.println("spring.datasource.username = " + env.getProperty("spring.datasource.username"));
        System.out.println("config locations (system) = " + env.getProperty("spring.config.location"));
    }
}
