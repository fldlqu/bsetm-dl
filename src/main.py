# -*- coding: utf-8 -*-
# 国家中小学智慧教育平台 资源下载工具 CLI v4.0
# 项目地址：https://github.com/happycola233/tchMaterial-parser

import re
import sys
import argparse
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from tqdm import tqdm

VERSION = "v4.0-cli"

CS_PATH_PREFIX = "cs_path:${ref-path}"
CDN_DOMAIN = "https://r1-ndr-private.ykt.cbern.com.cn"
API_BASE = "https://s-file-1.ykt.cbern.com.cn"
ASSETS_DOCUMENT = "assets_document"
THEMATIC_COURSE = "thematic_course"
DETAIL_URL = "https://basic.smartedu.cn/tchMaterial/detail?contentType={}&contentId={}&catalogType=tchMaterial&subCatalog=tchMaterial"

headers = {
    "Authorization": "Bearer 0",
    "X-ND-AUTH": 'MAC id="0",nonce="0",mac="0"'
}
client = httpx.Client()

def _get_resource_url(items: list) -> str | None:
    for item in items:
        if item["ti_is_source_file"]:
            url = item.get("ti_storage")
            if url:
                return url.replace(CS_PATH_PREFIX, CDN_DOMAIN)
            url = next((u for u in item["ti_storages"] if u), None)
            if url:
                return url


def parse(url: str) -> tuple[str, str] | tuple[None, None]:
    try:
        qs = parse_qs(urlparse(url).query)
        content_id = qs.get('contentId', [None])[0]
        content_type = qs.get('contentType', [ASSETS_DOCUMENT])[0]
        if not content_id:
            return None, None

        data = client.get(
            f"{API_BASE}/zxx/ndrs/special_edu/resources/details/{content_id}.json"
            if re.search(r"^https?://([^/]+)/syncClassroom/basicWork/detail", url) or content_type == THEMATIC_COURSE
            else f"{API_BASE}/zxx/ndrv2/resources/tch_material/details/{content_id}.json"
        ).json()
        title = data.get("title")

        resource_url = _get_resource_url(data["ti_items"])
        if not resource_url and content_type == THEMATIC_COURSE:
            for resource in client.get(f"{API_BASE}/zxx/ndrs/special_edu/thematic_course/{content_id}/resources/list.json").json():
                if resource["resource_type_code"] == ASSETS_DOCUMENT:
                    resource_url = _get_resource_url(resource["ti_items"])
                    if resource_url:
                        break

        return (resource_url, title) if resource_url else (None, None)

    except Exception as e:
        print(e); return None, None
def _download_stream(url: str, save_path: str, retry: int) -> bool:
    temp_path = f"{save_path}.tmp"
    for attempt in range(1, retry + 1):
        try:
            with client.stream("GET", url, headers=headers) as resp:
                if not resp.is_success:
                    print(f"服务器返回 HTTP 状态码 {resp.status_code}", file=sys.stderr)
                    if attempt < retry:
                        print(f"第 {attempt} 次失败，正在重试...", file=sys.stderr)
                    continue
                with open(temp_path, "wb") as f, tqdm(
                    total=int(resp.headers.get("Content-Length", 0)),
                    unit='B', unit_scale=True, desc=Path(save_path).name, ncols=80
                ) as pbar:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
                        pbar.update(len(chunk))
            Path(temp_path).replace(save_path)
            print(f"已保存：{save_path}")
            return True
        except Exception as e:
            print(f"第 {attempt} 次失败：{e}，正在重试..." if attempt < retry else e, file=sys.stderr)
    return False


def search_book(name: str) -> list:
    try:
        def parse_hierarchy(hierarchy):
            if not hierarchy:
                return {}
            parsed = {}
            for h in hierarchy:
                for ch in h["children"]:
                    parsed[ch["tag_id"]] = {
                        "display_name": ch["tag_name"],
                        "children": parse_hierarchy(ch["hierarchies"])
                    }
            return parsed

        hier = parse_hierarchy(
            client.get(f"{API_BASE}/zxx/ndrs/tags/tch_material_tag.json").json()["hierarchies"]
        )

        for url in client.get(f"{API_BASE}/zxx/ndrs/resources/tch_material/version/data_version.json").json()["urls"].split(","):
            for book in client.get(url).json():
                if not book.get("tag_paths"):
                    continue
                tag_paths = book["tag_paths"][0].split("/")[2:]
                temp_hier = hier[book["tag_paths"][0].split("/")[1]]
                if tag_paths[0] not in temp_hier["children"]:
                    continue
                edition_name = ""
                for i, p in enumerate(tag_paths):
                    if temp_hier["children"] and temp_hier["children"].get(p):
                        temp_hier = temp_hier["children"].get(p)
                        if i == 2:
                            edition_name = temp_hier["display_name"]
                if not temp_hier["children"]:
                    temp_hier["children"] = {}
                dn = book.get("title") or book.get("name") or f"(未知电子课本 {book['id']})"
                dn = dn.strip()
                providers = book.get("provider_list", [])
                publisher = providers[0].get("name", "").strip() if providers else ""
                if publisher and publisher != "智慧中小学":
                    dn = f"{dn}（{publisher}）"
                elif edition_name:
                    dn = f"{dn}（{edition_name}）"
                else:
                    sid = book["id"][-4:]
                    dn = f"{dn}（...{sid}）"
                book["display_name"] = dn
                temp_hier["children"][book["id"]] = book

        hits = {}

        def walk(d, path=""):
            for k, v in d.items():
                dn = v.get("display_name", "")
                if "children" in v and v["children"]:
                    walk(v["children"], f"{path}/{dn}")
                elif name in dn:
                    book_id = v.get("id", k)
                    key = (dn, book_id)
                    if key not in hits:
                        hits[key] = {"id": book_id, "name": dn, "type": v.get("resource_type_code", ASSETS_DOCUMENT)}

        walk(hier)
        return list(hits.values())
    except Exception as e:
        print(e)
        return []


def _dl_chunk(idx, start, end, url, save_path, retry, lock, pbar):
    part_path = Path(f"{save_path}.part.{idx}")
    for attempt in range(1, retry + 1):
        try:
            resp = httpx.Client().stream("GET", url, headers={**headers, "Range": f"bytes={start}-{end}"})
            with resp as r:
                if r.status_code not in (200, 206):
                    if attempt < retry:
                        print(f"分片 {idx} 第 {attempt} 次失败（HTTP {r.status_code}），正在重试...", file=sys.stderr)
                    continue
                with open(part_path, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
                        with lock:
                            pbar.update(len(chunk))
            return True
        except Exception as e:
            print(f"分片 {idx} 第 {attempt} 次失败：{e}，正在重试..." if attempt < retry else e, file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser(
        description=f"国家中小学智慧教育平台 资源下载工具 {VERSION}"
    )
    sub = parser.add_subparsers(dest='command', title='子命令')

    p_parse = sub.add_parser('parse', help='解析 URL，获取下载链接')
    p_parse.add_argument('urls', nargs='+', help='资源页面 URL')

    p_dl = sub.add_parser('download', help='按教材名称下载')
    p_dl.add_argument('names', nargs='+', help='教材名称（支持模糊搜索）')
    p_dl.add_argument('-o', '--output-dir', default='.', help='保存目录（默认：当前目录）')
    p_dl.add_argument('-t', '--threads', type=int, default=1, help='下载线程数（默认：1）')
    p_dl.add_argument('-r', '--retry', type=int, default=3, help='下载失败重试次数（默认：3）')

    p_search = sub.add_parser('search', help='搜索教材')
    p_search.add_argument('name', nargs='+', help='教材名称关键字')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    match args.command:
        case 'parse':
            for url in args.urls:
                resource_url, title = parse(url)
                print(resource_url or f"解析失败：{url}")
        case 'download':
            output_dir = Path(args.output_dir)
            if not output_dir.is_dir():
                output_dir.mkdir(parents=True, exist_ok=True)
            name = ' '.join(args.names)
            hits = search_book(name)
            if not hits:
                print(f"未找到匹配的教材：{name}", file=sys.stderr)
                return
            if len(hits) > 1:
                print(f"找到多个匹配的教材（{name}）：")
                for i, h in enumerate(hits, 1):
                    print(f"  {i}. {h['name']}")
                try:
                    sel = int(input("请选择序号（回车取消）："))
                    if sel < 1 or sel > len(hits):
                        return
                    book = hits[sel - 1]
                except (ValueError, EOFError):
                    return
            else:
                book = hits[0]

            url = DETAIL_URL.format(book['type'], book['id'])
            resource_url, title = parse(url)
            if not resource_url:
                print(f"解析失败：{book['name']}", file=sys.stderr)
                return

            save_path = output_dir / f"{title}.pdf" if title else output_dir / "download.pdf"
            if args.threads <= 1:
                _download_stream(resource_url, str(save_path), args.retry)
                return

            try:
                resp = client.head(resource_url, headers=headers)
                total = int(resp.headers.get("Content-Length", 0))
            except Exception as e:
                print(f"获取文件大小失败：{e}，回退单线程", file=sys.stderr)
                _download_stream(resource_url, str(save_path), args.retry)
                return

            if not total or resp.headers.get("Accept-Ranges", "").lower() != "bytes":
                print("服务器不支持分片下载，回退单线程", file=sys.stderr)
                _download_stream(resource_url, str(save_path), args.retry)
                return

            chunk_base = total // args.threads
            ranges = [(i * chunk_base, (total - 1 if i == args.threads - 1 else (i + 1) * chunk_base - 1)) for i in range(args.threads)]

            lock = threading.Lock()
            pbar = tqdm(total=total, unit='B', unit_scale=True, desc=save_path.name, ncols=80)

            with ThreadPoolExecutor(max_workers=args.threads) as ex:
                futures = {ex.submit(_dl_chunk, i, s, e, resource_url, str(save_path), args.retry, lock, pbar): i for i, (s, e) in enumerate(ranges)}
                ok = all(f.result() for f in as_completed(futures))

            pbar.close()

            if not ok:
                for i in range(args.threads):
                    Path(f"{save_path}.part.{i}").unlink(missing_ok=True)
                return

            temp_path = Path(f"{save_path}.tmp")
            with open(temp_path, "wb") as out:
                for i in range(args.threads):
                    part = Path(f"{save_path}.part.{i}")
                    out.write(part.read_bytes())
                    part.unlink()
            temp_path.replace(save_path)
            print(f"已保存：{save_path}")
        case 'search':
            name = ' '.join(args.name)
            hits = search_book(name)
            print('\n'.join(h['name'] for h in hits) if hits else f"未找到匹配的教材：{name}")


if __name__ == '__main__':
    main()
