import { handleTree } from "@/utils/tree";
import { useI18n } from "vue-i18n";
import { reactive, ref, onMounted, h, type Ref, shallowRef } from "vue";
import { isAllEmpty, isPhone, isEmail } from "@pureadmin/utils";
import { data_permissionApi } from "@/api/system/data_permission";
import { hasAuth } from "@/router/utils";
import type { OperationProps, SwPlusPageProps } from "@/components/SwPlusCrud";
export function useSysDataPermission(tableRef: Ref) {
  const { t } = useI18n();
  const api = reactive(data_permissionApi);
  api.update = api.patch;

  //固定按钮权限
  const auth = reactive({
    list: hasAuth("system:data_permission:list"),
    create: hasAuth("system:data_permission:create"),
    delete: hasAuth("system:data_permission:delete"),
    edit: hasAuth("system:data_permission:edit"),
    detail: hasAuth("system:data_permission:view")
  });
  const form = reactive({
    name: "",
    status: null
  });
  const dataList = ref([]);
  //列表
  const column=[
    {
      default: 0,
      required: false, //是否必填
      read_only: false, //是否只读
      label: "None",
      write_only: false, //是否只写
      prop: "old_id",
      help_text: "",
      choices: [], // 下拉菜单
      input_type: "string" //输入格式
    },
    {
      default: 0,
      required: false, //是否必填
      read_only: false, //是否只读
      label: "None",
      write_only: false, //是否只写
      prop: "mode_type",
      help_text: "",
      choices: [], // 下拉菜单
      input_type: "string" //输入格式
    },
    {
      default: 0,
      required: false, //是否必填
      read_only: false, //是否只读
      label: "None",
      write_only: false, //是否只写
      prop: "description",
      help_text: "",
      choices: [], // 下拉菜单
      input_type: "string" //输入格式
    },
    {
      default: 0,
      required: false, //是否必填
      read_only: false, //是否只读
      label: "None",
      write_only: false, //是否只写
      prop: "name",
      help_text: "",
      choices: [], // 下拉菜单
      input_type: "string" //输入格式
    },
    {
      default: 0,
      required: false, //是否必填
      read_only: false, //是否只读
      label: "None",
      write_only: false, //是否只写
      prop: "rules",
      help_text: "",
      choices: [], // 下拉菜单
      input_type: "string" //输入格式
    },
    {
      default: 0,
      required: false, //是否必填
      read_only: false, //是否只读
      label: "None",
      write_only: false, //是否只写
      prop: "is_active",
      help_text: "",
      choices: [], // 下拉菜单
      input_type: "string" //输入格式
    },
    {
      default: 0,
      required: false, //是否必填
      read_only: false, //是否只读
      label: "None",
      write_only: false, //是否只写
      prop: "dept_belong_id",
      help_text: "",
      choices: [], // 下拉菜单
      input_type: "string" //输入格式
    },
  ]
  const columns1 = [
    {
      default: 0,
      required: false, //是否必填
      read_only: false, //是否只读
      label: "上级岗位",
      write_only: false, //是否只写
      prop: "parent_id",
      help_text: "",
      choices: [], // 下拉菜单
      input_type: "object_related_field" //输入格式
    },
    {
      label: "岗位名称",
      prop: "name",
      align: "left",
      required: true, //是否必填
      read_only: false, //是否只读
      write_only: false, //是否只写
      help_text: "",
      input_type: "string",

      table_show: 1
    },
    {
      label: "岗位编码",
      prop: "code",
      required: true, //是否必填
      read_only: false, //是否只读
      write_only: true, //是否只写
      help_text: "",
      input_type: "string",
      table_show: 2
    },
    {
      default: 99,
      label: "排序",
      prop: "rank",
      required: false, //是否必填
      read_only: false, //是否只读
      write_only: false, //是否只写
      help_text: "",
      input_type: "integer",
      table_show: 3
    },
    {
      default: true,
      label: "岗位状态",
      prop: "enabled",
      required: false, //是否必填
      read_only: false, //是否只读
      write_only: false, //是否只写
      help_text: "",
      input_type: "boolean",
      table_show: 4
    },
    {
      label: "创建时间",
      minWidth: 200,
      required: false,
      read_only: true,
      write_only: false,
      prop: "created_time",
      help_text: "",
      input_type: "datetime",
      table_show: 5
    },
    {
      label: "备注",
      prop: "remark",
      required: false,
      write_only: false,
      input_type: "string",
      table_show: 6,
      read_only: false,
      minWidth: 320
    }
  ];
  //查询字段
  const searchColumnList = [
    {
      prop: "name",
      label: "岗位名称",
      help_text: "",
      input_type: "text",
      choices: [],
      default: ""
    },
    {
      prop: "status",
      label: "岗位状态",
      help_text: "",
      input_type: "select",
      choices: [
        {
          value: "true",
          label: "启用"
        },
        {
          value: "false",
          label: "停用"
        }
      ],
      default: ""
    }
  ];

  //新增/修改弹窗配置
  const addOrEditOptions = shallowRef<SwPlusPageProps["addOrEditOptions"]>({
    props: {
      row: {
        parent_id: ({ rawRow }) => {
          console.log(rawRow, rawRow?.parent_id ?? "");
          return rawRow?.parent_id ?? "";
        }
      },
      columns: {
        parent_id: ({ column }) => {
          column["valueType"] = "cascader";
          column["fieldProps"] = {
            ...column["fieldProps"],
            ...{
              valueOnClear: "",
              props: {
                value: "id",
                label: "name",
                emitPath: false,
                checkStrictly: true
              }
            }
          };
          column["options"] = dataList.value;
          return column;
        }
      },
      beforeSubmit: ({ formData, formOptions: { isAdd } }) => {
        // 发起请求前回调
        if (isAdd) {
          formData["parent_id"] = formData["parent_id"]
            ? formData["parent_id"]
            : 0;
        }
        return formData;
      },
      dialogOptions: {
        closeCallBack: ({ options, args }) => {
          if (!options?.props?.formInline?.id && args?.command === "sure") {
            //新增成功后刷新列表
            tableRef.value?.getPageColumn(false);
          }
          // onTrees();
        }
      }
    }
  });
  //扩展按钮，
  const operationButtonsProps = shallowRef<OperationProps>({
    width: 260, //操作框宽度
    buttons: [] //扩展按钮
    /**
     *  buttons: [
      {
        text: t("systemUser.editAvatar"),
        code: "upload",
        props: {
          type: "primary",
          icon: useRenderIcon(Avatar),
          plain: true,
          link: true
        },
        onClick: ({ row }) => {
          console.log("row");
          handleUpload(row);
        },
        show: auth.upload
      },
      {
        text: t("systemUser.resetPassword"),
        code: "reset",
        props: {
          type: "primary",
          icon: useRenderIcon(Password),
          link: true
        },
        onClick: ({ row }) => {
          handleReset(row);
        },
        show: auth.reset
      },
      {
        text: t("systemUser.assignRoles"),
        code: "role",
        props: {
          type: "primary",
          icon: useRenderIcon(Role),
          link: true
        },
        onClick: ({ row }) => {
          allocation(row, "role");
        },
        show: auth.role
      },
      {
        text: t("systemUser.assignPost"),
        code: "post",
        props: {
          type: "primary",
          icon: useRenderIcon(Post),
          link: true
        },
        onClick: ({ row }) => {
          allocation(row, "post");
        },
        show: auth.role
      }
    ]
     */
  });

  // 树形结构 特殊初始化数据
  async function onTrees() {
    const { data } = await api.list(); // 这里是返回一维数组结构，前端自行处理成树结构，返回格式要求：唯一id加父节点parentId，parentId取父节点id
    let newData = data.items;
    columns[0].choices = handleTree(newData);
    if (!isAllEmpty(form.name)) {
      // 前端搜索部门名称
      newData = newData.filter(item => item.name.includes(form.name));
    }
    if (!isAllEmpty(form.status)) {
      // 前端搜索状态
      newData = newData.filter(item => item.status === form.status);
    }
    dataList.value = handleTree(newData); // 处理成树结构
  }

  // function formatHigherDeptOptions(treeList) {
  //   // 根据返回数据的status字段值判断追加是否禁用disabled字段，返回处理后的树结构，用于上级部门级联选择器的展示（实际开发中也是如此，不可能前端需要的每个字段后端都会返回，这时需要前端自行根据后端返回的某些字段做逻辑处理）
  //   if (!treeList || !treeList.length) return;
  //   const newTreeList = [];
  //   for (let i = 0; i < treeList.length; i++) {
  //     treeList[i].disabled = treeList[i].status === 0 ? true : false;
  //     formatHigherDeptOptions(treeList[i].children);
  //     newTreeList.push(treeList[i]);
  //   }
  //   return newTreeList;
  // }

  onMounted(() => {
    onTrees();
  });

  return {
    api,
    auth,
    columns,
    searchColumnList,
    operationButtonsProps,
    addOrEditOptions
  };
}