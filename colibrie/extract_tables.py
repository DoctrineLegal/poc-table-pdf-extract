import fitz

from colibrie.tables import create_table, process_table, get_tables_candidates

from colibrie.intersection import get_intersection_between_horizontal_and_vertical_lines

from colibrie.segments import (
    get_segments,
    get_horizontal_segments,
    get_vertical_segments,
    merge_horizontal_segments,
    merge_vertical_segment,
    generate_missing_horizontal_segments,
    generate_missing_vertical_segments,
    normalize_segments,
)


def extract_tables(filepath, debug_mode=False):
    """
    :param: preserve_span: bool
        give a possibility to speed_up the execution
        by not preserving information about text position and only keeping
        the text content, can be useful for those with proper table aligned that
        do not need to do extra work with it
    """

    doc = fitz.Document(filepath)

    tables_lst = []

    for page in doc:
        # Always set the page rotation to 0 to prevent rotation from previous update of the PDF
        page.set_rotation(0)

        # GET SEGMENTS #

        segments = get_segments(page)

        vertical_segments = get_vertical_segments(segments)

        horizontal_segments = get_horizontal_segments(segments)

        # REMOVE OVERLAPPING SEGMENTS #

        vertical_segments = merge_vertical_segment(vertical_segments)

        horizontal_segments = merge_horizontal_segments(horizontal_segments)

        if not vertical_segments or not horizontal_segments:
            continue

        # NORMALIZE SEGMENT COORDINATE #

        normalize_segments(vertical_segments, horizontal_segments)

        # GET TABLES CANDIDATES #
        tables_candidates = get_tables_candidates(
            vertical_segments, horizontal_segments
        )

        for table_candidate in tables_candidates:

            vertical_segments = get_vertical_segments(table_candidate)

            horizontal_segments = get_horizontal_segments(table_candidate)

            # GENERATE MISSING SEGMENTS #

            distinct_y_lst = list(
                set([point.y for lines in vertical_segments for point in lines])
            )
            distinct_x_lst = list(
                set([point.x for lines in horizontal_segments for point in lines])
            )

            if not distinct_x_lst or not distinct_y_lst:
                continue

            range_y = (min(distinct_y_lst), max(distinct_y_lst))
            range_x = (min(distinct_x_lst), max(distinct_x_lst))

            # If the table does not meet the condition of a minimum size
            # we assume it is a bad table
            if (range_y[1] - range_y[0]) <= 20 and (range_x[1] - range_x[0]) <= 50:
                continue

            horizontal_segments = generate_missing_horizontal_segments(
                horizontal_segments, vertical_segments
            )

            vertical_segments = generate_missing_vertical_segments(
                horizontal_segments, vertical_segments
            )

            # GET INTERSECTIONS #

            intersections = get_intersection_between_horizontal_and_vertical_lines(
                horizontal_segments, vertical_segments
            )

            # If there is not a least 6 intersections point, it mean there is less than 2 cells
            # and it is not a valid table
            if not len(intersections) >= 6:
                continue

            # CREATE TABLE LIST #
            table = create_table(intersections, horizontal_segments, vertical_segments)

            # FILL TABLE #

            table = process_table(page, table, intersections)

            if not table:
                continue

            if debug_mode:
                pix = page.get_pixmap()
                table.debug.image = pix.tobytes()

            tables_lst.append(table)

    doc.close()

    return tables_lst
