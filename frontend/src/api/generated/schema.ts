export interface paths {
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_v1_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register */
        post: operations["register_api_v1_auth_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/boards/{board_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Board */
        get: operations["read_board_api_v1_boards__board_id__get"];
        put?: never;
        post?: never;
        /** Delete Board */
        delete: operations["delete_board_api_v1_boards__board_id__delete"];
        options?: never;
        head?: never;
        /** Update Board */
        patch: operations["update_board_api_v1_boards__board_id__patch"];
        trace?: never;
    };
    "/api/v1/boards/{board_id}/columns": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Column */
        post: operations["create_column_api_v1_boards__board_id__columns_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/boards/{board_id}/columns/order": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Reorder Columns */
        put: operations["reorder_columns_api_v1_boards__board_id__columns_order_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/boards/{board_id}/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Board Tasks */
        get: operations["list_board_tasks_api_v1_boards__board_id__tasks_get"];
        put?: never;
        /** Create Board Task */
        post: operations["create_board_task_api_v1_boards__board_id__tasks_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/columns/{column_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Column */
        delete: operations["delete_column_api_v1_columns__column_id__delete"];
        options?: never;
        head?: never;
        /** Update Column */
        patch: operations["update_column_api_v1_columns__column_id__patch"];
        trace?: never;
    };
    "/api/v1/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Live
         * @description The HTTP process is serving requests; this does not imply database readiness.
         */
        get: operations["health_live"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ready
         * @description The database is reachable and its migration heads exactly match this build.
         */
        get: operations["health_ready"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Projects */
        get: operations["list_projects_api_v1_projects_get"];
        put?: never;
        /** Create Project */
        post: operations["create_project_api_v1_projects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Project */
        get: operations["read_project_api_v1_projects__project_id__get"];
        put?: never;
        post?: never;
        /** Delete Project */
        delete: operations["delete_project_api_v1_projects__project_id__delete"];
        options?: never;
        head?: never;
        /** Update Project */
        patch: operations["update_project_api_v1_projects__project_id__patch"];
        trace?: never;
    };
    "/api/v1/projects/{project_id}/analytics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Project Analytics */
        get: operations["get_project_analytics_api_v1_projects__project_id__analytics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/boards": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Boards */
        get: operations["list_boards_api_v1_projects__project_id__boards_get"];
        put?: never;
        /** Create Board */
        post: operations["create_board_api_v1_projects__project_id__boards_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/members": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Members */
        get: operations["list_members_api_v1_projects__project_id__members_get"];
        put?: never;
        /** Add Member */
        post: operations["add_member_api_v1_projects__project_id__members_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/members/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Member */
        delete: operations["remove_member_api_v1_projects__project_id__members__user_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/owner": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Change Owner */
        put: operations["change_owner_api_v1_projects__project_id__owner_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}/tags": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Tags */
        get: operations["list_tags_api_v1_projects__project_id__tags_get"];
        put?: never;
        /** Create Tag */
        post: operations["create_tag_api_v1_projects__project_id__tags_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tags/{tag_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Tag */
        delete: operations["delete_tag_api_v1_tags__tag_id__delete"];
        options?: never;
        head?: never;
        /** Update Tag */
        patch: operations["update_tag_api_v1_tags__tag_id__patch"];
        trace?: never;
    };
    "/api/v1/tasks/{task_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Task */
        get: operations["get_task_api_v1_tasks__task_id__get"];
        put?: never;
        post?: never;
        /** Delete Task */
        delete: operations["delete_task_api_v1_tasks__task_id__delete"];
        options?: never;
        head?: never;
        /** Patch Task */
        patch: operations["patch_task_api_v1_tasks__task_id__patch"];
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/comments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Comments */
        get: operations["list_comments_api_v1_tasks__task_id__comments_get"];
        put?: never;
        /** Create Comment */
        post: operations["create_comment_api_v1_tasks__task_id__comments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List History */
        get: operations["list_history_api_v1_tasks__task_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tasks/{task_id}/move": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Move Task */
        post: operations["move_task_api_v1_tasks__task_id__move_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Users */
        get: operations["list_users_api_v1_users_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/{user_id}/role": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Change Role */
        patch: operations["change_role_api_v1_users__user_id__role_patch"];
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AnalyticsDto */
        AnalyticsDto: {
            /** Completion Over Time */
            completion_over_time: components["schemas"]["CompletionBucket"][];
            /**
             * From
             * Format: date
             */
            from: string;
            /**
             * Generated At
             * Format: date-time
             */
            generated_at: string;
            granularity: components["schemas"]["Granularity"];
            period: components["schemas"]["Period"];
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /** Status Distribution */
            status_distribution: components["schemas"]["StatusDistribution"][];
            /** Timezone */
            timezone: string;
            /**
             * To
             * Format: date
             */
            to: string;
        };
        /** AuditDto */
        AuditDto: {
            actor: components["schemas"]["Person"];
            /**
             * Actor Id
             * Format: uuid
             */
            actor_id: string;
            /** Changes */
            changes: components["schemas"]["Change"][];
            /** Event Type */
            event_type: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /**
             * Operation Id
             * Format: uuid
             */
            operation_id: string;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
        };
        /** BoardCreate */
        BoardCreate: {
            /** Name */
            name: string;
        };
        /** BoardDto */
        BoardDto: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /** Revision */
            revision: number;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** BoardPatch */
        BoardPatch: {
            /** Name */
            name: string;
        };
        /** BoardSnapshot */
        BoardSnapshot: {
            board: components["schemas"]["BoardDto"];
            /** Columns */
            columns: components["schemas"]["ColumnDto"][];
            /** Members */
            members: components["schemas"]["MemberDto"][];
            project: components["schemas"]["ProjectDto"];
            /** Revision */
            revision: number;
            /**
             * Server Time
             * Format: date-time
             */
            server_time: string;
            /** Tags */
            tags: components["schemas"]["TagDto"][];
            /** Tasks */
            tasks: components["schemas"]["TaskDto"][];
        };
        /** Change */
        Change: {
            /** Field */
            field: string;
            new_value: components["schemas"]["JsonValue"];
            old_value: components["schemas"]["JsonValue"];
        };
        /** ChangeRoleRequest */
        ChangeRoleRequest: {
            /**
             * Role
             * @enum {string}
             */
            role: "admin" | "pm" | "developer";
        };
        /** ColumnCreate */
        ColumnCreate: {
            /**
             * Category
             * @enum {string}
             */
            category: "todo" | "in_progress" | "done";
            /** Name */
            name: string;
        };
        /** ColumnDto */
        ColumnDto: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /**
             * Category
             * @enum {string}
             */
            category: "todo" | "in_progress" | "done";
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Position */
            position: number;
        };
        /** ColumnOrder */
        ColumnOrder: {
            /** Column Ids */
            column_ids: string[];
            /** Expected Revision */
            expected_revision: number;
        };
        /** ColumnPatch */
        ColumnPatch: {
            /** Name */
            name: string;
        };
        /** CommentCreate */
        CommentCreate: {
            /** Text */
            text: string;
        };
        /** CommentDto */
        CommentDto: {
            author: components["schemas"]["Person"];
            /**
             * Author Id
             * Format: uuid
             */
            author_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /** Text */
            text: string;
        };
        /** CompletionBucket */
        CompletionBucket: {
            /** Completed Count */
            completed_count: number;
            /**
             * Date
             * Format: date
             */
            date: string;
        };
        /** Credentials */
        Credentials: {
            /** Email */
            email: string;
            /**
             * Password
             * Format: password
             */
            password: string;
        };
        /** ErrorBody */
        ErrorBody: {
            /** Code */
            code: string;
            /** Details */
            details?: components["schemas"]["ErrorDetail"][];
            /** Message */
            message: string;
            /** Request Id */
            request_id: string;
        };
        /** ErrorDetail */
        ErrorDetail: {
            /** Field */
            field: string;
            /** Message */
            message: string;
        };
        /** ErrorResponse */
        ErrorResponse: {
            error: components["schemas"]["ErrorBody"];
        };
        /** @enum {string} */
        Granularity: "day" | "month";
        JsonValue: unknown;
        /** LiveResponse */
        LiveResponse: {
            /**
             * Status
             * @default ok
             * @constant
             */
            status: "ok";
        };
        /** MemberCreate */
        MemberCreate: {
            /** Email */
            email: string;
        };
        /** MemberDto */
        MemberDto: {
            /** Email */
            email: string;
            /** Is Active */
            is_active: boolean;
            /** Is Owner */
            is_owner: boolean;
            /**
             * Joined At
             * Format: date-time
             */
            joined_at: string;
            /** Name */
            name: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** MutationResponse[BoardDto] */
        MutationResponse_BoardDto_: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /** Board Revision */
            board_revision: number;
            data: components["schemas"]["BoardDto"];
        };
        /** MutationResponse[ColumnDto] */
        MutationResponse_ColumnDto_: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /** Board Revision */
            board_revision: number;
            data: components["schemas"]["ColumnDto"];
        };
        /** MutationResponse[CommentDto] */
        MutationResponse_CommentDto_: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /** Board Revision */
            board_revision: number;
            data: components["schemas"]["CommentDto"];
        };
        /** MutationResponse[NoneType] */
        MutationResponse_NoneType_: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /** Board Revision */
            board_revision: number;
            /** Data */
            data: null;
        };
        /** MutationResponse[TaskDto] */
        MutationResponse_TaskDto_: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /** Board Revision */
            board_revision: number;
            data: components["schemas"]["TaskDto"];
        };
        /** MutationResponse[list[ColumnDto]] */
        MutationResponse_list_ColumnDto__: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /** Board Revision */
            board_revision: number;
            /** Data */
            data: components["schemas"]["ColumnDto"][];
        };
        /** OwnerChange */
        OwnerChange: {
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** PaginatedList[AuditDto] */
        PaginatedList_AuditDto_: {
            /** Items */
            items: components["schemas"]["AuditDto"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Total */
            total: number;
        };
        /** PaginatedList[BoardDto] */
        PaginatedList_BoardDto_: {
            /** Items */
            items: components["schemas"]["BoardDto"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Total */
            total: number;
        };
        /** PaginatedList[CommentDto] */
        PaginatedList_CommentDto_: {
            /** Items */
            items: components["schemas"]["CommentDto"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Total */
            total: number;
        };
        /** PaginatedList[MemberDto] */
        PaginatedList_MemberDto_: {
            /** Items */
            items: components["schemas"]["MemberDto"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Total */
            total: number;
        };
        /** PaginatedList[ProjectDto] */
        PaginatedList_ProjectDto_: {
            /** Items */
            items: components["schemas"]["ProjectDto"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Total */
            total: number;
        };
        /** PaginatedList[TagDto] */
        PaginatedList_TagDto_: {
            /** Items */
            items: components["schemas"]["TagDto"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Total */
            total: number;
        };
        /** PaginatedList[UserDto] */
        PaginatedList_UserDto_: {
            /** Items */
            items: components["schemas"]["UserDto"][];
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
            /** Total */
            total: number;
        };
        /** @enum {string} */
        Period: "week" | "month" | "all";
        /** Person */
        Person: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
        };
        /** ProjectCreate */
        ProjectCreate: {
            /**
             * Description
             * @default
             */
            description: string;
            /** Key */
            key: string;
            /** Name */
            name: string;
            /**
             * Timezone
             * @default UTC
             */
            timezone: string;
        };
        /** ProjectDto */
        ProjectDto: {
            /** Board Count */
            board_count: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Description */
            description: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Key */
            key: string;
            /** Member Count */
            member_count: number;
            /** Name */
            name: string;
            /**
             * Owner Id
             * Format: uuid
             */
            owner_id: string;
            /** Timezone */
            timezone: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ProjectPatch */
        ProjectPatch: {
            /** Description */
            description?: string;
            /** Name */
            name?: string;
        };
        /** ReadyResponse */
        ReadyResponse: {
            /**
             * Status
             * @default ready
             * @constant
             */
            status: "ready";
        };
        /** RegisterRequest */
        RegisterRequest: {
            /** Email */
            email: string;
            /** Name */
            name: string;
            /**
             * Password
             * Format: password
             */
            password: string;
        };
        /** SessionDto */
        SessionDto: {
            /** Csrf Token */
            csrf_token: string;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            user: components["schemas"]["UserDto"];
        };
        /** StatusDistribution */
        StatusDistribution: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /** Board Name */
            board_name: string;
            /**
             * Category
             * @enum {string}
             */
            category: "todo" | "in_progress" | "done";
            /**
             * Column Id
             * Format: uuid
             */
            column_id: string;
            /** Column Name */
            column_name: string;
            /** Count */
            count: number;
        };
        /** TagCreate */
        TagCreate: {
            /**
             * Color
             * @default #64748B
             */
            color: string;
            /** Name */
            name: string;
        };
        /** TagDto */
        TagDto: {
            /** Color */
            color: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
        };
        /** TagPatch */
        TagPatch: {
            /** Color */
            color?: string;
            /** Name */
            name?: string;
        };
        /** TaskCreate */
        TaskCreate: {
            /** Assignee Id */
            assignee_id?: string | null;
            /**
             * Column Id
             * Format: uuid
             */
            column_id: string;
            /** Deadline */
            deadline?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Priority
             * @default medium
             * @enum {string}
             */
            priority: "low" | "medium" | "high";
            /** Story Points */
            story_points?: number | null;
            /** Tag Ids */
            tag_ids?: string[];
            /** Title */
            title: string;
        };
        /** TaskDto */
        TaskDto: {
            assignee: components["schemas"]["Person"] | null;
            /** Assignee Id */
            assignee_id: string | null;
            /** Assignee Is Project Member */
            assignee_is_project_member: boolean;
            author: components["schemas"]["Person"];
            /**
             * Author Id
             * Format: uuid
             */
            author_id: string;
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /**
             * Column Id
             * Format: uuid
             */
            column_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Deadline */
            deadline: string | null;
            /** Description */
            description: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Is Completed */
            is_completed: boolean;
            /** Key */
            key: string;
            /** Number */
            number: number;
            /** Position */
            position: number;
            /**
             * Priority
             * @enum {string}
             */
            priority: "low" | "medium" | "high";
            /**
             * Project Id
             * Format: uuid
             */
            project_id: string;
            /** Story Points */
            story_points: number | null;
            /** Tag Ids */
            tag_ids: string[];
            /** Title */
            title: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** TaskList */
        TaskList: {
            /** Board Revision */
            board_revision: number;
            /** Items */
            items: components["schemas"]["TaskDto"][];
            /** Total */
            total: number;
        };
        /** TaskMove */
        TaskMove: {
            /** Before Task Id */
            before_task_id: string | null;
            /**
             * Column Id
             * Format: uuid
             */
            column_id: string;
            /** Expected Version */
            expected_version: number;
        };
        /** TaskPatch */
        TaskPatch: {
            /** Assignee Id */
            assignee_id?: string | null;
            /** Deadline */
            deadline?: string | null;
            /** Description */
            description?: string;
            /** Expected Version */
            expected_version: number;
            /**
             * Priority
             * @enum {string}
             */
            priority?: "low" | "medium" | "high";
            /** Story Points */
            story_points?: number | null;
            /** Tag Ids */
            tag_ids?: string[];
            /** Title */
            title?: string;
        };
        /** TaskRead */
        TaskRead: {
            /**
             * Board Id
             * Format: uuid
             */
            board_id: string;
            /** Board Revision */
            board_revision: number;
            data: components["schemas"]["TaskDto"];
        };
        /** UserDto */
        UserDto: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Email */
            email: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Is Active */
            is_active: boolean;
            /** Name */
            name: string;
            /**
             * Role
             * @enum {string}
             */
            role: "admin" | "pm" | "developer";
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    login_api_v1_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Credentials"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Слишком много запросов */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    me_api_v1_auth_me_get: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    register_api_v1_auth_register_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegisterRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserDto"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    read_board_api_v1_boards__board_id__get: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                board_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BoardSnapshot"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_board_api_v1_boards__board_id__delete: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                board_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_board_api_v1_boards__board_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                board_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BoardPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_BoardDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_column_api_v1_boards__board_id__columns_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                board_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ColumnCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_ColumnDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reorder_columns_api_v1_boards__board_id__columns_order_put: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                board_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ColumnOrder"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_list_ColumnDto__"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_board_tasks_api_v1_boards__board_id__tasks_get: {
        parameters: {
            query?: {
                assignee_id?: string | null;
                tag_ids?: string[] | null;
                deadline_from?: string | null;
                deadline_to?: string | null;
                priority?: ("low" | "medium" | "high")[] | null;
                column_ids?: string[] | null;
                q?: string | null;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                board_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskList"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_board_task_api_v1_boards__board_id__tasks_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                board_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_TaskDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_column_api_v1_columns__column_id__delete: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                column_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_column_api_v1_columns__column_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                column_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ColumnPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_ColumnDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    health_live: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LiveResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    health_ready: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadyResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_projects_api_v1_projects_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedList_ProjectDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_project_api_v1_projects_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    read_project_api_v1_projects__project_id__get: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_project_api_v1_projects__project_id__delete: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_project_api_v1_projects__project_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_project_analytics_api_v1_projects__project_id__analytics_get: {
        parameters: {
            query?: {
                period?: components["schemas"]["Period"];
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalyticsDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_boards_api_v1_projects__project_id__boards_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedList_BoardDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_board_api_v1_projects__project_id__boards_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BoardCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BoardDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_members_api_v1_projects__project_id__members_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedList_MemberDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    add_member_api_v1_projects__project_id__members_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemberCreate"];
            };
        };
        responses: {
            /** @description Пользователь уже состоит в проекте */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberDto"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemberDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    remove_member_api_v1_projects__project_id__members__user_id__delete: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    change_owner_api_v1_projects__project_id__owner_put: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OwnerChange"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_tags_api_v1_projects__project_id__tags_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedList_TagDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_tag_api_v1_projects__project_id__tags_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TagCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_tag_api_v1_tags__tag_id__delete: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                tag_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_tag_api_v1_tags__tag_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                tag_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TagPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_task_api_v1_tasks__task_id__get: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TaskRead"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_task_api_v1_tasks__task_id__delete: {
        parameters: {
            query: {
                expected_version: number;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_NoneType_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    patch_task_api_v1_tasks__task_id__patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_TaskDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_comments_api_v1_tasks__task_id__comments_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedList_CommentDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_comment_api_v1_tasks__task_id__comments_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommentCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_CommentDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_history_api_v1_tasks__task_id__history_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedList_AuditDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    move_task_api_v1_tasks__task_id__move_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TaskMove"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MutationResponse_TaskDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Сервис временно недоступен */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_users_api_v1_users_get: {
        parameters: {
            query?: {
                q?: string;
                limit?: number;
                offset?: number;
            };
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PaginatedList_UserDto_"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    change_role_api_v1_users__user_id__role_patch: {
        parameters: {
            query?: never;
            header?: {
                /** @description Для POST/PATCH/PUT/DELETE укажите csrf_token из ответа /auth/login или /auth/me. Для GET не требуется. */
                "X-CSRF-Token"?: string | null;
            };
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChangeRoleRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserDto"];
                };
            };
            /** @description Войдите в систему */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Недостаточно прав */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Ресурс не найден */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Изменения конфликтуют с текущим состоянием */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Проверьте заполнение полей */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Внутренняя ошибка сервера */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
}
