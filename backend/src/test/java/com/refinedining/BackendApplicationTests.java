package com.refinedining;

import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
import com.refinedining.domain.food.refined.repository.FoodMaterialRepository;
import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.transaction.support.TransactionTemplate;

@SpringBootTest
@EnableAutoConfiguration(exclude = {
        DataSourceAutoConfiguration.class,
        HibernateJpaAutoConfiguration.class
})
class BackendApplicationTests {

    @MockBean
    private RawFoodMaterialRepository rawFoodMaterialRepository;

    @MockBean
    private FoodMaterialRepository foodMaterialRepository;

    @MockBean
    private TransactionTemplate transactionTemplate;

    @Test
    void contextLoads() {
    }

}
