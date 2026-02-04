package com.refinedining.domain.food.refined.repository;

import com.refinedining.domain.food.refined.entity.FoodMaterial;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface FoodMaterialRepository extends JpaRepository<FoodMaterial, Long> {
    @Query("SELECT DISTINCT f FROM FoodMaterial f " +
            "LEFT JOIN FETCH f.children " +
            "WHERE f.name LIKE %:name% AND f.parent IS NULL")
    List<FoodMaterial> findByNameWithChildren(@Param("name") String name);
}
