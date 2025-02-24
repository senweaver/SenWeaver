import { BaseApi } from "@/api/utils/base";
import { DocsApi } from "@/api/utils/utils";
export const data_permissionApi = new BaseApi(DocsApi("system/data_permission"));