from pathlib import Path

from project.crawler.crawler_1.packages.description_filter import (
    filter_description
)

from project.crawler.crawler_1.packages.food_filter import (
    extract_food_candidates
)

from project.crawler.crawler_1.packages.logging_handler import (
    get_logger
)

from project.crawler.crawler_1.packages.selenium_handler import (
    create_driver,
    load_page,
    close_driver
)

from project.crawler.crawler_1.packages.utils import (
    clean_text,
    normalize_text,
    extract_opening_hours,
    extract_price,
    load_url_file,
    save_json
)


# =========================================================
# LOGGER
# =========================================================

logger = get_logger(
    "crawl_food_details"
)


# =========================================================
# FILE URL CỦA 12 QUẬN
# =========================================================

DISTRICT_FILES = {
    "Ba Đình": "ba_dinh.txt",
    "Bắc Từ Liêm": "bac_tu_liem.txt",
    "Cầu Giấy": "cau_giay.txt",
    "Đống Đa": "dong_da.txt",
    "Hà Đông": "ha_dong.txt",
    "Hai Bà Trưng": "hai_ba_trung.txt",
    "Hoàn Kiếm": "hoan_kiem.txt",
    "Hoàng Mai": "hoang_mai.txt",
    "Long Biên": "long_bien.txt",
    "Nam Từ Liêm": "nam_tu_liem.txt",
    "Tây Hồ": "tay_ho.txt",
    "Thanh Xuân": "thanh_xuan.txt",
}


# =========================================================
# OUTPUT
# =========================================================

OUTPUT_FILE = Path(
    "data/raw/dataset1_hanoi.json"
)


# =========================================================
# TẠO ITEM
# =========================================================

def build_item(
    candidate,
    source
):
    name = clean_text(
        candidate.get(
            "name",
            ""
        )
    )

    district = clean_text(
        candidate.get(
            "district",
            ""
        )
    )

    category = clean_text(
        candidate.get(
            "category",
            "Quán ăn"
        )
    )

    address = clean_text(
        candidate.get(
            "address",
            ""
        )
    )

    text = clean_text(
        candidate.get(
            "text",
            ""
        )
    )

    # -----------------------------------------------------
    # NAME
    # -----------------------------------------------------

    if not name:
        return None

    # -----------------------------------------------------
    # DISTRICT
    # -----------------------------------------------------

    if not district:

        logger.info(
            f"[DROP - NO DISTRICT] "
            f"{source} | "
            f"{name}"
        )

        return None

    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    if not text:

        logger.info(
            f"[DROP - NO TEXT] "
            f"{district} | "
            f"{source} | "
            f"{name}"
        )

        return None

    # -----------------------------------------------------
    # GIỜ MỞ CỬA
    # -----------------------------------------------------

    opening_hours = (
        extract_opening_hours(
            text
        )
        or ""
    )

    # -----------------------------------------------------
    # MỨC GIÁ
    # -----------------------------------------------------

    price_range = (
        extract_price(
            text
        )
        or ""
    )

    # -----------------------------------------------------
    # BẮT BUỘC CÓ GIỜ
    # -----------------------------------------------------

    if not opening_hours:

        logger.info(
            f"[DROP - NO HOURS] "
            f"{district} | "
            f"{source} | "
            f"{name}"
        )

        return None

    # -----------------------------------------------------
    # BẮT BUỘC CÓ GIÁ
    # -----------------------------------------------------

    if not price_range:

        logger.info(
            f"[DROP - NO PRICE] "
            f"{district} | "
            f"{source} | "
            f"{name}"
        )

        return None

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    description = (
        filter_description(
            name,
            text
        )
        or ""
    )

    # -----------------------------------------------------
    # INTERNAL DATA
    #
    # _address chỉ dùng để chống trùng.
    # Không ghi vào dataset cuối.
    # -----------------------------------------------------

    return {
        "name": name,

        "district": district,

        "category": category,

        "opening_hours": (
            opening_hours
        ),

        "price_range": (
            price_range
        ),

        "suitable_for": (
            "Gia đình, Cặp đôi, Nhóm bạn"
        ),

        "weather_fit": (
            "Trong nhà"
        ),

        "description": (
            description
        ),

        "_address": (
            address
        )
    }


# =========================================================
# DUPLICATE KEY
# =========================================================

def make_new_key(item):
    """
    Dùng:
        name + district + address

    Address chỉ dùng nội bộ.
    """

    return (
        normalize_text(
            item.get(
                "name",
                ""
            )
        ),
        normalize_text(
            item.get(
                "district",
                ""
            )
        ),
        normalize_text(
            item.get(
                "_address",
                ""
            )
        )
    )


# =========================================================
# TÌM QUÁN TRÙNG
# =========================================================

def find_duplicate_key(
    collected,
    new_item
):
    """
    Quy tắc:

    Cùng tên + cùng quận:
        - nếu cả hai có address và address khác nhau:
            -> xem là 2 cơ sở khác nhau

        - nếu address giống nhau:
            -> duplicate

        - nếu một bên không có address:
            -> coi là duplicate để tránh cùng quán
               từ PasGo / Vincom / GreenSM...
               bị lặp lại
    """

    new_name = normalize_text(
        new_item.get(
            "name",
            ""
        )
    )

    new_district = normalize_text(
        new_item.get(
            "district",
            ""
        )
    )

    new_address = normalize_text(
        new_item.get(
            "_address",
            ""
        )
    )

    for key, old_item in (
        collected.items()
    ):

        old_name = normalize_text(
            old_item.get(
                "name",
                ""
            )
        )

        old_district = normalize_text(
            old_item.get(
                "district",
                ""
            )
        )

        if old_name != new_name:
            continue

        if old_district != new_district:
            continue

        old_address = normalize_text(
            old_item.get(
                "_address",
                ""
            )
        )

        # Cả hai có địa chỉ
        if (
            old_address
            and new_address
        ):

            # Cùng địa chỉ
            if old_address == new_address:
                return key

            # Khác địa chỉ
            # -> hai cơ sở khác nhau
            continue

        # Một trong hai thiếu địa chỉ
        # nhưng cùng tên + quận
        return key

    return None


# =========================================================
# MERGE DUPLICATE
# =========================================================

def merge_duplicate(
    old_item,
    new_item
):
    # -----------------------------------------------------
    # CATEGORY
    #
    # Nếu bất kỳ nguồn nào nhận ra là Quán nước
    # thì ưu tiên Quán nước.
    # -----------------------------------------------------

    if (
        new_item.get(
            "category"
        )
        == "Quán nước"
    ):
        old_item[
            "category"
        ] = "Quán nước"

    # -----------------------------------------------------
    # DESCRIPTION DÀI HƠN
    # -----------------------------------------------------

    old_description = clean_text(
        old_item.get(
            "description",
            ""
        )
    )

    new_description = clean_text(
        new_item.get(
            "description",
            ""
        )
    )

    if (
        len(new_description)
        > len(old_description)
    ):
        old_item[
            "description"
        ] = new_description

    # -----------------------------------------------------
    # ADDRESS
    # -----------------------------------------------------

    if (
        not old_item.get(
            "_address"
        )
        and new_item.get(
            "_address"
        )
    ):
        old_item[
            "_address"
        ] = new_item[
            "_address"
        ]

    return old_item


# =========================================================
# CRAWL 1 QUẬN
# =========================================================

def crawl_district(
    driver,
    district,
    filename,
    collected
):

    path = (
        Path("data/links")
        / filename
    )

    if not path.exists():

        logger.warning(
            f"[NO FILE] "
            f"{path}"
        )

        return

    lines = load_url_file(
        path
    )

    logger.info("")
    logger.info(
        "========================================"
    )
    logger.info(
        f"QUẬN: {district}"
    )
    logger.info(
        f"SỐ URL: {len(lines)}"
    )
    logger.info(
        "========================================"
    )

    seen_urls = set()

    # -----------------------------------------------------
    # DUYỆT URL
    # -----------------------------------------------------

    for line in lines:

        # Format:
        # source|url

        parts = line.split(
            "|",
            1
        )

        if len(parts) != 2:

            logger.warning(
                f"[INVALID FORMAT] "
                f"{line}"
            )

            continue

        source = clean_text(
            parts[0]
        )

        url = clean_text(
            parts[1]
        )

        if not source:

            logger.warning(
                f"[NO SOURCE] "
                f"{line}"
            )

            continue

        if not url:

            logger.warning(
                f"[NO URL] "
                f"{line}"
            )

            continue

        # -------------------------------------------------
        # URL DUPLICATE
        # -------------------------------------------------

        url_key = (
            url.lower()
            .rstrip("/")
        )

        if url_key in seen_urls:

            logger.info(
                f"[SKIP DUP URL] "
                f"{source} | "
                f"{url}"
            )

            continue

        seen_urls.add(
            url_key
        )

        # -------------------------------------------------
        # LOAD PAGE
        # -------------------------------------------------

        logger.info(
            f"[CRAWL] "
            f"{district} | "
            f"{source} | "
            f"{url}"
        )

        try:

            html = load_page(
                driver,
                url
            )

        except Exception as exc:

            logger.error(
                f"[LOAD ERROR] "
                f"{source} | "
                f"{url} | "
                f"{exc}"
            )

            continue

        # -------------------------------------------------
        # EXTRACT CANDIDATES
        # -------------------------------------------------

        try:

            candidates = (
                extract_food_candidates(
                    html=html,
                    expected_district=(
                        district
                    ),
                    base_url=url
                )
            )

        except Exception as exc:

            logger.error(
                f"[FILTER ERROR] "
                f"{source} | "
                f"{url} | "
                f"{exc}"
            )

            continue

        logger.info(
            f"[CANDIDATES] "
            f"{source} | "
            f"{len(candidates)}"
        )

        # -------------------------------------------------
        # BUILD ITEM
        # -------------------------------------------------

        for candidate in candidates:

            item = build_item(
                candidate=(
                    candidate
                ),
                source=source
            )

            if item is None:
                continue

            # ---------------------------------------------
            # TÌM DUPLICATE
            # ---------------------------------------------

            duplicate_key = (
                find_duplicate_key(
                    collected,
                    item
                )
            )

            if duplicate_key is not None:

                collected[
                    duplicate_key
                ] = merge_duplicate(
                    collected[
                        duplicate_key
                    ],
                    item
                )

                logger.info(
                    f"[MERGE] "
                    f"{district} | "
                    f"{source} | "
                    f"{item['name']}"
                )

                continue

            # ---------------------------------------------
            # QUÁN MỚI
            # ---------------------------------------------

            key = make_new_key(
                item
            )

            collected[
                key
            ] = item

            logger.info(
                f"[KEEP] "
                f"{district} | "
                f"{source} | "
                f"{item['category']} | "
                f"{item['name']} | "
                f"{item['opening_hours']} | "
                f"{item['price_range']}"
            )


# =========================================================
# TẠO DATASET CUỐI
# =========================================================

def create_final_dataset(
    collected
):

    items = list(
        collected.values()
    )

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    items.sort(
        key=lambda item: (
            normalize_text(
                item.get(
                    "district",
                    ""
                )
            ),
            normalize_text(
                item.get(
                    "category",
                    ""
                )
            ),
            normalize_text(
                item.get(
                    "name",
                    ""
                )
            )
        )
    )

    final_data = []

    # -----------------------------------------------------
    # ĐÁNH ID
    # -----------------------------------------------------

    for index, item in enumerate(
        items,
        start=1
    ):

        final_data.append(
            {
                "id": (
                    f"hn_loc_"
                    f"{index:03d}"
                ),

                "name": (
                    item.get(
                        "name",
                        ""
                    )
                ),

                "district": (
                    item.get(
                        "district",
                        ""
                    )
                ),

                "category": (
                    item.get(
                        "category",
                        "Quán ăn"
                    )
                ),

                "opening_hours": (
                    item.get(
                        "opening_hours",
                        ""
                    )
                ),

                "price_range": (
                    item.get(
                        "price_range",
                        ""
                    )
                ),

                "suitable_for": (
                    "Gia đình, Cặp đôi, Nhóm bạn"
                ),

                "weather_fit": (
                    "Trong nhà"
                ),

                "description": (
                    item.get(
                        "description",
                        ""
                    )
                )
            }
        )

    return final_data


# =========================================================
# MAIN
# =========================================================

def main():

    logger.info(
        "========================================"
    )

    logger.info(
        "BẮT ĐẦU CRAWL ĐỊA ĐIỂM ĂN UỐNG HÀ NỘI"
    )

    logger.info(
        "========================================"
    )

    collected = {}

    driver = None

    try:

        driver = create_driver()

        # -------------------------------------------------
        # CRAWL 12 QUẬN
        # -------------------------------------------------

        for district, filename in (
            DISTRICT_FILES.items()
        ):

            crawl_district(
                driver=driver,
                district=district,
                filename=filename,
                collected=collected
            )

    finally:

        if driver is not None:

            close_driver(
                driver
            )

    # -----------------------------------------------------
    # FINAL DATASET
    # -----------------------------------------------------

    final_data = (
        create_final_dataset(
            collected
        )
    )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    save_json(
        OUTPUT_FILE,
        final_data
    )

    # -----------------------------------------------------
    # THỐNG KÊ
    # -----------------------------------------------------

    food_count = sum(
        1
        for item in final_data
        if item.get(
            "category"
        ) == "Quán ăn"
    )

    drink_count = sum(
        1
        for item in final_data
        if item.get(
            "category"
        ) == "Quán nước"
    )

    logger.info("")
    logger.info(
        "========================================"
    )

    logger.info(
        f"TỔNG ĐỊA ĐIỂM: "
        f"{len(final_data)}"
    )

    logger.info(
        f"QUÁN ĂN: "
        f"{food_count}"
    )

    logger.info(
        f"QUÁN NƯỚC: "
        f"{drink_count}"
    )

    logger.info(
        f"DATASET: "
        f"{OUTPUT_FILE}"
    )

    logger.info(
        "========================================"
    )


if __name__ == "__main__":
    main()