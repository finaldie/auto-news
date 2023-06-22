SQL_TABLE_CREATION_PATCH = """
CREATE TABLE IF NOT EXISTS `patch` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(256) NOT NULL,
  `order_id` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT NOW(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""


SQL_TABLE_CREATION_INDEX_PAGES = """
CREATE TABLE IF NOT EXISTS `index_pages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `category` varchar(256) NOT NULL,
  `name` varchar(256) NOT NULL,
  `index_id` varchar(256) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT NOW(),
  `updated_at` datetime NOT NULL DEFAULT NOW(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `category_name` (`category`,`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""
