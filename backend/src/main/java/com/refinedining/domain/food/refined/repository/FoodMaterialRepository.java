package com.refinedining.domain.food.refined.repository;

import com.refinedining.domain.food.refined.entity.FoodMaterial;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface FoodMaterialRepository extends JpaRepository<FoodMaterial, Long> {

    /**
     * 부모(원재료) 식품을 페이지네이션하여 조회합니다.
     * 컬렉션(children)은 hibernate.default_batch_fetch_size를 통해 IN 쿼리로 일괄 로딩하여
     * Fetch Join + Pageable 사용 시 발생하는 인메모리 페이징(HHH90003004) 문제를 방지합니다.
     */
    @Query("SELECT f FROM FoodMaterial f " +
            "WHERE f.parent IS NULL AND f.name LIKE CONCAT('%', :name, '%') " +
            "ORDER BY CASE " +
            "  WHEN f.name = :name THEN 0 " +
            "  WHEN f.name LIKE CONCAT(:name, '%') THEN 1 " +
            "  ELSE 2 " +
            "END, f.name ASC, f.id ASC")
    List<FoodMaterial> findByNameWithChildren(@Param("name") String name, Pageable pageable);

    @Query("SELECT c FROM FoodMaterial c JOIN FETCH c.parent WHERE c.id = :id")
    Optional<FoodMaterial> findChildWithParentById(@Param("id") Long id);

    @Modifying(clearAutomatically = true, flushAutomatically = true)
    @Query("DELETE FROM FoodMaterial f WHERE f.parent IS NOT NULL")
    void deleteAllChildrenInBatch();

    @Modifying(clearAutomatically = true, flushAutomatically = true)
    @Query("DELETE FROM FoodMaterial f WHERE f.parent IS NULL")
    void deleteAllParentsInBatch();
}
